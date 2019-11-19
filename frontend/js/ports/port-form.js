import ConditionVariable               from '$qui/base/condition-variable.js'
import {AssertionError, TimeoutError}  from '$qui/base/errors.js'
import {gettext}                       from '$qui/base/i18n.js'
import {mix}                           from '$qui/base/mixwith.js'
import {ChoiceButtonsField}            from '$qui/forms/common-fields.js'
import {PageForm}                      from '$qui/forms/common-forms.js'
import FormButton                      from '$qui/forms/form-button.js'
import {ValidationError, ErrorMapping} from '$qui/forms/forms.js'
import {ConfirmMessageForm}            from '$qui/messages/common-message-forms.js'
import * as Messages                   from '$qui/messages/messages.js'
import * as Toast                      from '$qui/messages/toast.js'
import * as ArrayUtils                 from '$qui/utils/array.js'
import * as ObjectUtils                from '$qui/utils/object.js'
import * as PromiseUtils               from '$qui/utils/promise.js'
import * as StringUtils                from '$qui/utils/string.js'

import * as API         from '$app/api.js'
import * as Cache       from '$app/cache.js'
import AttrdefFormMixin from '$app/common/attrdef-form-mixin.js'
import * as Common      from '$app/common/common.js'

import * as Ports from './ports.js'


const DISABLED_PORT_VISIBLE_ATTRS = ['id', 'enabled']
const VALUE_CHANGE_TIMEOUT = 1000

const logger = Ports.logger


/**
 * @class QToggle.PortsSection.PortForm
 * @extends qui.forms.PageForm
 * @param {String} portId
 * @param {String} [deviceName]
 */
export default class PortForm extends mix(PageForm).with(AttrdefFormMixin) {

    constructor(portId, deviceName) {
        let pathId = portId
        if (deviceName && !Cache.isMainDevice(deviceName)) {
            pathId = portId.substring(deviceName.length + 1)
        }

        super({
            pathId: pathId,
            keepPrevVisible: true,
            closeOnApply: false,
            title: '', /* Set dynamically, later */
            icon: Ports.PORT_ICON,

            buttons: [
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true}),
                new FormButton({id: 'apply', caption: gettext('Apply'), def: true})
            ]
        })

        this._portId = portId
        this._deviceName = deviceName

        this._fullAttrdefs = {}
        this._whenValueChanged = null
    }

    init() {
        this.updateUI()
    }

    /**
     * Updates the entire form (fields & values) from the port.
     */
    updateUI(fieldChangeWarnings = true) {
        let port = Cache.getPort(this.getPortId())
        if (!port) {
            throw new AssertionError(`Port with id ${this.getPortId()} not found in cache`)
        }

        let device = null
        if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
            device = Cache.getSlaveDevice(this._deviceName)
        }

        let title = port.display_name
        if (!title) {
            title = port.id
            if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                title = title.substring(this._deviceName.length + 1)
            }
        }

        this.setTitle(title)
        this.setIcon(Ports.makePortIcon(port))

        /* Create a clone of the port attributes, so that some attributes can be tweaked, for a better/simpler
         * representation */
        let origPort = port
        port = ObjectUtils.copy(port, /* deep = */ true)

        /* Preprocess type attribute */
        if (port.type === 'number') {
            if (port.integer) {
                port.type = gettext('Integer Number')
                delete port.integer
            }
            else {
                port.type = gettext('Number')
            }
        }
        else /* Assuming port.type === 'boolean' */ {
            port.type = gettext('Boolean')
        }

        /* Remove the tag attribute */
        delete port.tag

        let attrdefs = ObjectUtils.copy(port.definitions, /* deep = */ true)

        /* Merge in some additional attribute definitions that we happen to know of */
        ObjectUtils.forEach(API.ADDITIONAL_PORT_ATTRDEFS, function (name, def) {
            def = ObjectUtils.copy(def, /* deep = */ true)

            if (name in attrdefs) {
                attrdefs[name] = ObjectUtils.combine(attrdefs[name], def)
            }
            else {
                attrdefs[name] = def
            }
        })

        /* Combine standard and additional attribute definitions */
        this._fullAttrdefs = Common.combineAttrdefs(API.STD_PORT_ATTRDEFS, attrdefs)

        /* Group device_*_expressions together (with expression) */
        let sepAbove = 'expression' in port
        ArrayUtils.range(1, 9).forEach(function (i) {

            /* Build "device_..._device_expression" string */
            let ds = ArrayUtils.range(0, i).map(() => 'device')

            /* Only consider attributes actually exposed by port */
            let attrName = `${ds.join('_')}_expression`
            if (!(attrName in port)) {
                return
            }

            /* Start from the default device_expression definition */
            let def = this._fullAttrdefs['device_expression']

            /* Work on copy */
            def = this._fullAttrdefs[attrName] = ObjectUtils.copy(def, /* deep = */ true)

            if (i === 1) {
                def.display_name = gettext('Device Expression')
            }
            else {
                def.display_name = StringUtils.formatPercent(
                    gettext('Device%(nth)s Expression'),
                    {nth: `<sup>(${i})</sup>`}
                )
            }

            /* Place the device expression attributes right after the simple expression one */
            def.order = API.STD_PORT_ATTRDEFS['expression'].order + i

            /* Make sure there's a separator above expressions */
            if (!sepAbove) {
                def.separator = true
                sepAbove = true
            }

        }, this)

        if (!port.enabled) {
            /* Filter out attribute definitions not visible when port disabled */
            this._fullAttrdefs = ObjectUtils.filter(this._fullAttrdefs, function (name, def) {
                return DISABLED_PORT_VISIBLE_ATTRS.indexOf(name) >= 0
            })
        }

        /* Filter out attribute definitions not applicable to port */
        this._fullAttrdefs = ObjectUtils.filter(this._fullAttrdefs, function (name, def) {
            let showAnyway = def.showAnyway
            if (typeof showAnyway === 'function') {
                showAnyway = showAnyway(port, this._fullAttrdefs)
            }
            return def.common || showAnyway || (name in port)
        }, this)

        /* Make sure there's a separator above expressions */
        if (!sepAbove) {
            if (this._fullAttrdefs.transform_write) {
                this._fullAttrdefs.transform_write = ObjectUtils.copy(
                    this._fullAttrdefs.transform_write,
                    /* deep = */ true
                )
                this._fullAttrdefs.transform_write.separator = true
            }
            else if (this._fullAttrdefs.transform_read) {
                this._fullAttrdefs.transform_read = ObjectUtils.copy(
                    this._fullAttrdefs.transform_read,
                    /* deep = */ true
                )
                this._fullAttrdefs.transform_read.separator = true
            }
        }

        /* Make sure all defs have a valueToUI function */
        // TODO once AttrDef becomes a class, this will no longer be necessary */
        ObjectUtils.forEach(this._fullAttrdefs, function (name, def) {
            if (!def.valueToUI) {
                def.valueToUI = function (value) {
                    return value
                }
            }
        })

        /* Prepend "device_" to each provisioning expression attribute, since it actually refers to the slave attribute,
         * not the master's */
        let provisioning = (port.provisioning || []).map(function (name) {

            if (name === 'expression' || name.match(new RegExp('^(device_)+expression'))) {
                name = `device_${name}`
            }

            return name

        })

        /* Prepare form fields */
        this.fieldsFromAttrdefs({
            attrdefs: this._fullAttrdefs,
            initialData: port,
            provisioning: provisioning,
            fieldChangeWarnings: fieldChangeWarnings
        })
        this._addValueField(origPort)

        /* Remove button */
        this.removeButton('remove')
        if (port.virtual && (!device || device.online)) {
            /* Virtual ports can be removed */
            this.addButton(0, new FormButton({
                id: 'remove',
                caption: gettext('Remove'),
                style: 'danger'
            }))
        }

    }

    getPortId() {
        return this._portId
    }

    setWaitingValueChanged() {
        if (this._whenValueChanged) {
            throw new AssertionError('Attempt to wait for value change while already waiting')
        }

        this._whenValueChanged = new ConditionVariable()

        PromiseUtils.withTimeout(this._whenValueChanged, VALUE_CHANGE_TIMEOUT).catch(function (error) {

            if (error instanceof TimeoutError) {
                logger.debug(`value-change not received within timeout for ${this._portId}, reverting to current one`)
                let port = Cache.getPort(this._portId)
                if (!port) {
                    return
                }

                this.setData({value: port.value})
            }

            /* Other errors can practically only be generated by cancelling the condition variable */

        }.bind(this))
    }

    clearWaitingValueChanged() {
        if (!this._whenValueChanged) {
            throw new AssertionError('Attempt to cancel waiting for value change while not waiting')
        }

        this._whenValueChanged.cancel()
        this._whenValueChanged = null
    }

    isWaitingValueChanged() {
        return !!this._whenValueChanged
    }

    applyData(data) {
        let port = Cache.getPort(this.getPortId())
        if (!port) {
            throw new AssertionError(`Port with id ${this.getPortId()} not found in cache`)
        }

        let newValue = null
        let newAttrs = {}
        let changedFields = this.getChangedFields()

        changedFields.forEach(function (fieldName) {
            let value = data[fieldName]
            if (value == null) {
                throw new AssertionError(`Got null value for changed field ${fieldName}`)
            }

            /* Skip value field, as it is treated separately */
            if (fieldName === 'value') {
                newValue = value
                return
            }

            /* We're interested only in attributes */
            if (!fieldName.startsWith('attr_')) {
                return
            }

            let name = fieldName.substring(5)

            /* Ignore non-modifiable or undefined attributes */
            if (!(name in this._fullAttrdefs) || !this._fullAttrdefs[name].modifiable) {
                return
            }

            logger.debug(`updating port attribute "${this.getPortId()}.${name}" to ${JSON.stringify(value)}`)
            newAttrs[name] = value

        }, this)

        let patchPortPromise = Promise.resolve()
        if (Object.keys(newAttrs).length) {
            patchPortPromise = API.patchPort(port.id, newAttrs).then(function () {

                logger.debug(`port "${port.id}" attributes successfully updated`)
                Toast.info(gettext('Port has been updated.'))

            }).catch(function (error) {

                logger.errorStack(`failed to update port "${port.id}" attributes`, error)

                let m
                if (error instanceof API.APIError && (m = error.messageCode.match(/invalid field: (.*)/))) {
                    let fieldName = `attr_${m[1]}`
                    throw new ErrorMapping({[fieldName]: new ValidationError(gettext('Invalid value.'))})
                }

                throw error

            })
        }

        let patchValuePromise = Promise.resolve()
        if (newValue != null) {
            /* Adapt port value */
            if (port.type === 'number') {
                if (port.integer) {
                    newValue = parseInt(newValue)
                }
                else {
                    newValue = parseFloat(newValue)
                }
            }

            if (port.value === newValue) {
                patchValuePromise = Promise.resolve()
            }
            else {
                logger.debug(`updating port "${port.id}" value to ${JSON.stringify(newValue)}`)

                patchValuePromise = API.patchPortValue(port.id, newValue).then(function () {

                    logger.debug(`port "${port.id}" value set`)

                    if (this.isWaitingValueChanged()) {
                        this.clearWaitingValueChanged()
                    }

                    this.setWaitingValueChanged()

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to set port "${port.id}" value`, error)
                    throw error

                })
            }
        }

        return patchPortPromise.then(() => patchValuePromise)
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'remove':
                this.pushPage(this.makeRemovePortForm())

                break
        }
    }

    _addValueField(port) {
        this.removeField('value')

        if (!port.enabled) {
            return null
        }

        let fieldAttrs
        let FieldClass
        if (port.type === 'boolean') {
            FieldClass = ChoiceButtonsField
            fieldAttrs = {
                choices: [
                    {label: gettext('Off'), value: false},
                    {label: gettext('On'), value: true}
                ]
            }
        }
        else { /* Assuming number */
            /* We can use the port as an attribute definition */
            let def = ObjectUtils.copy(port)

            /* Only validate integer constraint if port has no transform attribute set */
            if (def.integer && (port.transform_write || port.transform_read)) {
                def.integer = false
            }

            fieldAttrs = this.fieldAttrsFromAttrdef('value', def)

            FieldClass = ObjectUtils.pop(fieldAttrs, 'class')
        }

        fieldAttrs.name = 'value'
        fieldAttrs.description = gettext('Current port value.')
        fieldAttrs.label = gettext('Value')
        fieldAttrs.required = false
        fieldAttrs.unit = port.unit
        fieldAttrs.separator = true
        fieldAttrs.readonly = !port.writable
        fieldAttrs.initialValue = port.value

        let valueField = new FieldClass(fieldAttrs)
        this.addField(-1, valueField)

        if ((port.provisioning || []).indexOf('value') >= 0) {
            valueField.setWarning(gettext('Value will be provisioned when device gets back online.'))
        }

        return valueField
    }

    navigate(pathId) {
        let port = Cache.getPort(this.getPortId())
        if (!port) {
            throw new AssertionError(`Port with id ${this.getPortId()} not found in cache`)
        }

        switch (pathId) {
            case 'remove':
                if (port.virtual) {
                    return this.makeRemovePortForm()
                }
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeRemovePortForm() {
        let port = Cache.getPort(this.getPortId())
        if (!port) {
            throw new AssertionError(`Port with id ${this.getPortId()} not found in cache`)
        }

        let msg = StringUtils.formatPercent(
            gettext('Really remove %(object)s?'),
            {object: Messages.wrapLabel(port.display_name || port.id)}
        )

        return ConfirmMessageForm.show(
            msg,
            /* onYes = */ function () {

                logger.debug(`removing port "${port.id}"`)

                let portId = port.id
                if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                    API.setSlave(this._deviceName)
                    portId = portId.substring(this._deviceName.length + 1)
                }
                API.deletePort(portId).then(function () {

                    logger.debug(`port "${port.id}" successfully removed`)
                    this.close()

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to remove port "${port.id}"`, error)
                    Toast.error(error.message)

                })

            }.bind(this),
            /* onNo = */ null, /* pathId = */ 'remove'
        )
    }

}

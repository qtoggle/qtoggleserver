import ConditionVariable              from '$qui/base/condition-variable.js'
import {AssertionError, TimeoutError} from '$qui/base/errors.js'
import {gettext}                      from '$qui/base/i18n.js'
import {mix}                          from '$qui/base/mixwith.js'
import {ChoiceButtonsField}           from '$qui/forms/common-fields.js'
import {PageForm}                     from '$qui/forms/common-forms.js'
import FormButton                     from '$qui/forms/form-button.js'
import {ConfirmMessageForm}           from '$qui/messages/common-message-forms.js'
import * as Messages                  from '$qui/messages/messages.js'
import * as Toast                     from '$qui/messages/toast.js'
import * as ArrayUtils                from '$qui/utils/array.js'
import * as ObjectUtils               from '$qui/utils/object.js'
import * as PromiseUtils              from '$qui/utils/promise.js'
import * as StringUtils               from '$qui/utils/string.js'

import * as API         from '$app/api.js'
import * as Cache       from '$app/cache.js'
import AttrdefFormMixin from '$app/common/attrdef-form-mixin.js'
import * as Common      from '$app/common/common.js'

import * as Ports from './ports.js'


const DISABLED_PORT_VISIBLE_ATTRS = ['id', 'enabled']

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
            title: '',
            icon: Ports.PORT_ICON,
            continuousValidation: true,

            buttons: [
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true})
            ]
        })

        this._portId = portId
        this._deviceName = deviceName

        this._fullAttrdefs = {}
        this._whenPortEnabled = null
    }

    init() {
        this.updateUI()
    }

    /**
     * Updates the entire form (fields & values) from the port.
     */
    updateUI() {
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
        this.fieldsFromAttrdefs(
            this._fullAttrdefs,
            /* extraFieldOptions = */ undefined,
            /* initialData = */ port,
            /* provisioning = */ provisioning
        )
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

    setWaitingPortEnabled() {
        if (this._whenPortEnabled) {
            throw new AssertionError('Attempt to wait for port to become enabled while already waiting')
        }

        this.setProgress()

        this._whenPortEnabled = new ConditionVariable()

        PromiseUtils.withTimeout(this._whenPortEnabled, API.SERVER_TIMEOUT * 1000).catch(function (error) {

            if (error instanceof TimeoutError) {
                this.setError(gettext('Port could not be enabled.'))
            }

            /* Other errors can practically only be generated by cancelling the condition variable */

        }.bind(this)).then(function () {

            this.clearProgress()

        }.bind(this))
    }

    clearWaitingPortEnabled() {
        if (!this._whenPortEnabled) {
            throw new AssertionError('Attempt to cancel waiting for port to become enabled while not waiting')
        }

        this.clearProgress()
        this._whenPortEnabled.cancel()
        this._whenPortEnabled = null
    }

    isWaitingPortEnabled() {
        return !!this._whenPortEnabled
    }

    applyField(value, fieldName) {
        let port = Cache.getPort(this.getPortId())
        if (!port) {
            throw new AssertionError(`Port with id ${this.getPortId()} not found in cache`)
        }

        if (fieldName === 'value') {
            if (value == null) {
                return
            }

            let newValue
            if (port.type === 'boolean') {
                newValue = value
            }
            else if (port.integer) { /* Assuming number */
                newValue = parseInt(value)
            }
            else {
                newValue = parseFloat(value)
            }

            if (port.value === newValue) {
                return Promise.resolve()
            }

            logger.debug(`updating port "${this.getPortId()}" value to ${JSON.stringify(newValue)}`)

            return API.postPortValue(port.id, newValue).then(function () {

                logger.debug(`port "${port.id}" value set`)

            }).catch(function (error) {

                logger.errorStack(`failed to set port "${port.id}" value`, error)
                throw error

            })
        }
        else if (fieldName.startsWith('attr_')) { /* A port attribute */
            let name = fieldName.substring(5)
            if (!(name in this._fullAttrdefs) || !this._fullAttrdefs[name].modifiable) {
                return
            }

            if (name === 'enabled' && value) {
                this.setWaitingPortEnabled()
            }

            logger.debug(`updating port attribute "${this.getPortId()}.${name}" to ${JSON.stringify(value)}`)

            let newAttrs = {[name]: value}

            return API.patchPort(port.id, newAttrs).then(function () {

                /* clearProgress() will be called later, as soon as port-update event arrives */
                logger.debug(`port attribute "${port.id}.${name}" successfully updated`)

            }).catch(function (error) {

                if (this.isWaitingPortEnabled()) {
                    this.clearWaitingPortEnabled()
                }

                logger.errorStack(`failed to update port attribute "${port.id}.${name}"`, error)
                throw error

            }.bind(this))
        }
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
                    Toast.error(error.toString())

                })

            }.bind(this),
            /* onNo = */ null, /* pathId = */ 'remove'
        )
    }

}

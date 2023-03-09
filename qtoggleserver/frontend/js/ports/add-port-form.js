
import {gettext}            from '$qui/base/i18n.js'
import {CheckField}         from '$qui/forms/common-fields/common-fields.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields/common-fields.js'
import {NumericField}       from '$qui/forms/common-fields/common-fields.js'
import {TextField}          from '$qui/forms/common-fields/common-fields.js'
import {PageForm}           from '$qui/forms/common-forms/common-forms.js'
import FormButton           from '$qui/forms/form-button.js'
import {ValidationError}    from '$qui/forms/forms.js'
import * as Navigation      from '$qui/navigation.js'

import * as BaseAPI          from '$app/api/base.js'
import * as DevicesAPI       from '$app/api/devices.js'
import * as NotificationsAPI from '$app/api/notifications.js'
import * as PortsAPI         from '$app/api/ports.js'
import * as Cache            from '$app/cache.js'

import * as Ports from './ports.js'


const VALID_ID_REGEX = new RegExp('^[_a-zA-Z.][_a-zA-Z0-9.-]*$')

const logger = Ports.logger


/**
 * @alias qtoggle.ports.AddPortForm
 * @extends qui.forms.commonforms.PageForm
 */
class AddPortForm extends PageForm {

    /**
     * @constructs
     * @param {String} deviceName
     */
    constructor(deviceName) {
        super({
            icon: Ports.PORT_ICON,
            title: gettext('Add Virtual Port...'),
            pathId: 'add',
            continuousValidation: true,
            keepPrevVisible: true,

            fields: [
                new TextField({
                    name: 'id',
                    label: gettext('Identifier'),
                    required: true,
                    placeholder: 'my_port_1',

                    validate(id) {
                        if (!id.match(VALID_ID_REGEX)) {
                            let msg = gettext('Only letters, digits, underscores and dots are permitted.')
                            throw new ValidationError(msg)
                        }
                    }
                }),
                new ChoiceButtonsField({
                    name: 'type',
                    label: gettext('Type'),
                    required: true,
                    choices: [
                        {value: 'boolean', label: gettext('Boolean')},
                        {value: 'number', label: gettext('Number')}
                    ],
                    onChange: (value, form) => form._updateFieldsVisibility()
                }),
                new NumericField({
                    name: 'min',
                    label: gettext('Minimum Value'),
                    hidden: true,
                    onChange: (value, form) => form._updateFieldsVisibility()
                }),
                new NumericField({
                    name: 'max',
                    label: gettext('Maximum Value'),
                    hidden: true
                }),
                new CheckField({
                    name: 'integer',
                    label: gettext('Integer'),
                    hidden: true,
                    onChange: (value, form) => form._updateFieldsVisibility()
                }),
                new NumericField({
                    name: 'step',
                    label: gettext('Step'),
                    hidden: true
                })
                // TODO choices
            ],
            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'add', caption: gettext('Add'), def: true})
            ]
        })

        this._deviceName = deviceName
    }

    applyData(data) {
        let portId = data.id

        let deviceName = this._deviceName || Cache.getMainDevice().name

        logger.debug(`adding port "${portId}"`)

        BaseAPI.setSlaveName(this._deviceName)
        return DevicesAPI.getDevice().then(function (attrs) {

            if (!attrs.virtual_ports) {
                logger.warn(`device "${deviceName}" does not support virtual ports`)
                throw new Error(gettext('Device does not support virtual ports.'))
            }

        }).then(function () {

            BaseAPI.setSlaveName(this._deviceName)

            let min, max, integer, step, choices
            if (data.type === 'number') {
                min = data.min
                max = data.max
                integer = data.integer
                step = data.step
                choices = data.choices
            }

            return PortsAPI.postPorts(portId, data.type, min, max, integer, step, choices)

        }.bind(this)).then(function () {

            logger.debug(`port "${portId}" successfully added`)

            let fullPortId = portId
            if (deviceName !== Cache.getMainDevice().name) {
                fullPortId = deviceName + `.${fullPortId}`
            }
            NotificationsAPI.waitExpectedEvent('port-add', {id: fullPortId}).then(function () {
                Navigation.navigate({path: Cache.getPortPath(portId, deviceName)})
            }).catch(() => {}) /* We don't really care about expected event waiting errors */

        }).catch(function (error) {

            logger.errorStack(`failed to add port "${portId}"`, error)
            throw error

        })
    }

    _updateFieldsVisibility() {
        let data = this.getUnvalidatedData()

        if (data.type === 'number') {
            this.getField('min').show()
            this.getField('max').show()
            this.getField('integer').show()
            if (data.min != null) {
                this.getField('step').show()
            }
            else {
                this.getField('step').hide()
            }
        }
        else {
            this.getField('min').hide()
            this.getField('max').hide()
            this.getField('integer').hide()
            this.getField('step').hide()
        }
    }

}


export default AddPortForm

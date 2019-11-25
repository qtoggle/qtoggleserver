import {gettext}                                                 from '$qui/base/i18n.js'
import {CheckField, ChoiceButtonsField, NumericField, TextField} from '$qui/forms/common-fields.js'
import {PageForm}                                                from '$qui/forms/common-forms.js'
import FormButton                                                from '$qui/forms/form-button.js'
import {ValidationError}                                         from '$qui/forms/forms.js'

import * as API   from '$app/api.js'
import * as Cache from '$app/cache.js'

import * as Ports from './ports.js'


const VALID_ID_REGEX = new RegExp('^[_a-zA-Z.][_a-zA-Z0-9.]*$')

const logger = Ports.logger


/**
 * @class AddPortForm
 * @extends qui.forms.PageForm
 * @private
 * @param {String} deviceName
 */
export default class AddPortForm extends PageForm {

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
                    continuousChange: true,

                    validate(id) {
                        if (!id.match(VALID_ID_REGEX)) {
                            let msg = gettext('Only letters, digits and underscores are permitted.')
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
                    continuousChange: true,
                    onChange: (value, form) => form._updateFieldsVisibility()
                }),
                new NumericField({
                    name: 'max',
                    label: gettext('Maximum Value'),
                    hidden: true,
                    continuousChange: true
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
                    continuousChange: true,
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

        API.setSlave(this._deviceName)
        return API.getDevice().then(function (attrs) {

            if (!attrs.virtual_ports) {
                logger.warn(`device "${deviceName}" does not support virtual ports`)
                throw new Error(gettext('Device does not support virtual ports.'))
            }

        }).then(function () {

            API.setSlave(this._deviceName)

            let min, max, integer, step, choices
            if (data.type === 'number') {
                min = data.min
                max = data.max
                integer = data.integer
                step = data.step
                choices = data.choices
            }

            return API.postPorts(portId, data.type, min, max, integer, step, choices)

        }.bind(this)).then(function () {

            logger.debug(`port "${portId}" successfully added`)

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

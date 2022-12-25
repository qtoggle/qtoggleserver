
import {gettext}         from '$qui/base/i18n.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {TextAreaField}   from '$qui/forms/common-fields/common-fields.js'
import {PageForm}        from '$qui/forms/common-forms/common-forms.js'
import FormButton        from '$qui/forms/form-button.js'
import {ValidationError} from '$qui/forms/forms.js'

import * as PeripheralsAPI from '$app/api/peripherals.js'

import * as Peripherals from './peripherals.js'


const VALID_ID_REGEX = new RegExp('^[_a-zA-Z.][_a-zA-Z0-9.-]*$')

const logger = Peripherals.logger


/**
 * @alias qtoggle.peripheral.AddPeripheralForm
 * @extends qui.forms.commonforms.PageForm
 */
class AddPeripheralForm extends PageForm {

    /**
     * @constructs
     */
    constructor() {
        super({
            icon: Peripherals.PERIPHERAL_ICON,
            title: gettext('Add Peripheral...'),
            pathId: 'add',
            continuousValidation: true,
            keepPrevVisible: true,

            fields: [
                new TextField({
                    name: 'name',
                    label: gettext('Name'),
                    required: false,
                    placeholder: 'my_peripheral',

                    validate(name) {
                        if (name && !name.match(VALID_ID_REGEX)) {
                            let msg = gettext('Only letters, digits, underscores and dots are permitted.')
                            throw new ValidationError(msg)
                        }
                    }
                }),
                new TextField({
                    name: 'driver',
                    label: gettext('Driver'),
                    required: true
                }),
                new TextAreaField({
                    name: 'params',
                    label: gettext('Parameters'),
                    required: false,
                    rows: 30,
                    resize: 'vertical',

                    validate(params) {
                        try {
                            JSON.parse(params)
                        }
                        catch (e) {
                            let msg = gettext('Enter a valid JSON')
                            throw new ValidationError(msg)
                        }
                    }
                })
            ],
            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true}),
                new FormButton({id: 'add', caption: gettext('Add'), def: true})
            ]
        })
    }

    applyData(data) {
        logger.debug(`adding peripheral of driver "${data.driver}"`)

        return PeripheralsAPI.postPeripherals(
            data.driver, JSON.parse(data.params), data.name || null
        ).then(function (peripheral) {
            logger.debug(`peripheral "${peripheral.id}" successfully added`)
            let peripheralsSection = this.getSection()
            peripheralsSection.updatePeripheralsList()
        }.bind(this)).catch(function (error) {
            logger.errorStack(`failed to add peripheral of driver "${data.driver}"`, error)
            throw error
        })
    }

}


export default AddPeripheralForm

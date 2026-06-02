import {gettext}            from '$qui/base/i18n.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields/common-fields.js'
import {TextAreaField}      from '$qui/forms/common-fields/common-fields.js'
import {TextField}          from '$qui/forms/common-fields/common-fields.js'
import {PageForm}           from '$qui/forms/common-forms/common-forms.js'
import FormButton           from '$qui/forms/form-button.js'
import {ValidationError}    from '$qui/forms/forms.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as PeripheralsAPI from '$app/api/peripherals.js'
import * as Utils          from '$app/utils.js'

import * as Peripherals from './peripherals.js'


const logger = Peripherals.logger


/**
 * @alias qtoggle.peripherals.PeripheralForm
 * @extends qui.forms.commonforms.PageForm
 */
class PeripheralForm extends PageForm {

    /**
     * @constructs
     * @param {String} peripheralId
     */
    constructor(peripheralId) {
        let pathId = `~${peripheralId}`

        super({
            pathId: pathId,
            keepPrevVisible: true,
            title: '', /* Set dynamically, later */
            icon: Peripherals.PERIPHERAL_ICON,

            fields: [
                new TextField({
                    name: 'name',
                    label: gettext('Name'),
                    required: false,
                    readonly: true
                }),
                new TextField({
                    name: 'driver',
                    label: gettext('Driver'),
                    required: true,
                    readonly: true
                }),
                new TextAreaField({
                    name: 'params',
                    label: gettext('Parameters'),
                    required: false,
                    readonly: true,
                    rows: 30,
                    resize: 'vertical',
                    cssClass: 'params-text-area',

                    validate(params) {
                        if (!params) {
                            return
                        }
                        try {
                            JSON.parse(params)
                        }
                        catch {
                            throw new ValidationError(gettext('Enter a valid JSON'))
                        }
                    }
                }),
                new ChoiceButtonsField({
                    name: 'force_enabled',
                    label: gettext('Force Enabled'),
                    required: false,
                    readonly: true,
                    choices: [
                        {value: false, label: gettext('Disabled')},
                        {value: null, label: gettext('Auto')},
                        {value: true, label: gettext('Enabled')}
                    ]
                })
            ],

            buttons: [
                new FormButton({id: 'cancel', caption: gettext('Cancel'), cancel: true})
            ]
        })

        this._peripheralId = peripheralId
    }

    load() {
        return PeripheralsAPI.getPeripherals().then(function (peripherals) {
            let peripheral = peripherals.find(p => p.id === this._peripheralId)
            if (peripheral) {
                this.setData({
                    name: peripheral.name,
                    driver: peripheral.driver,
                    params: JSON.stringify(peripheral.params || {}, null, 4),
                    force_enabled: peripheral.force_enabled
                })
                this.setTitle(peripheral.id)
                if (!peripheral.static) {
                    this.getField('name').setReadonly(false)
                    this.getField('driver').setReadonly(false)
                    this.getField('params').setReadonly(false)
                    this.getField('force_enabled').setReadonly(false)
                    this.addButton(-1, new FormButton({id: 'remove', caption: gettext('Remove'), style: 'danger'}))
                    this.addButton(-1, new FormButton({id: 'apply', caption: gettext('Apply'), def: true}))
                }
            }
            else {
                throw new Error(gettext(`Peripheral ${this._peripheralId} could not be found`))
            }
        }.bind(this))
    }

    applyData(data) {
        let params = data.params ? JSON.parse(data.params) : {}
        let payload = {
            driver: data.driver,
            name: data.name || null,
            force_enabled: data.force_enabled,
            params: params
        }

        logger.debug(`updating peripheral "${this._peripheralId}"`)

        return PeripheralsAPI.patchPeripheral(this._peripheralId, payload).then(function (peripheral) {

            logger.debug(`peripheral "${this._peripheralId}" successfully updated`)
            this._peripheralId = peripheral.id

        }.bind(this)).catch(function (error) {

            logger.errorStack(`failed to update peripheral "${this._peripheralId}"`, error)
            throw error

        })
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'remove':
                this.pushPage(this.makeRemovePeripheralForm())
                break
        }
    }

    navigate(pathId) {
        switch (pathId) {
            case 'remove':
                return this.makeRemovePeripheralForm()
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeRemovePeripheralForm() {
        let msg = StringUtils.formatPercent(
            gettext('Really remove peripheral %(object)s?'),
            {object: Messages.wrapLabel(this._peripheralId)}
        )

        return new ConfirmMessageForm({
            message: msg,
            onYes: function () {

                logger.debug(`removing peripheral "${this._peripheralId}"`)

                PeripheralsAPI.deletePeripheral(this._peripheralId).then(function () {

                    logger.debug(`peripheral "${this._peripheralId}" successfully removed`)
                    this.close(/* force = */ true)

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to remove peripheral "${this._peripheralId}"`, error)
                    Utils.showToastError(error)

                }.bind(this))

            }.bind(this),
            pathId: 'remove'
        })
    }

    /**
     * @returns {String}
     */
    getPeripheralId() {
        return this._peripheralId
    }

}


export default PeripheralForm

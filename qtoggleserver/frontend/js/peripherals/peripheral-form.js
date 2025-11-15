import {gettext}            from '$qui/base/i18n.js'
import {TextAreaField}      from '$qui/forms/common-fields/common-fields.js'
import {TextField}          from '$qui/forms/common-fields/common-fields.js'
import {PageForm}           from '$qui/forms/common-forms/common-forms.js'
import FormButton           from '$qui/forms/form-button.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as ObjectUtils     from '$qui/utils/object.js'
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
                    resize: 'vertical'
                })
            ],

            buttons: [
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true})
            ]
        })

        this._peripheralId = peripheralId
    }

    load() {
        return PeripheralsAPI.getPeripherals().then(function (peripherals) {
            let peripheral = peripherals.find(p => p.id === this._peripheralId)
            if (peripheral) {
                let data = ObjectUtils.copy(peripheral)
                ObjectUtils.pop(data, 'id')
                let name = ObjectUtils.pop(data, 'name')
                let driver = ObjectUtils.pop(data, 'driver')
                let isStatic = ObjectUtils.pop(data, 'static')
                this.setData({
                    name: name,
                    driver: driver,
                    params: JSON.stringify(data, null, 4)
                })
                this.setTitle(peripheral.id)
                if (!isStatic) {
                    this.addButton(0, new FormButton({id: 'remove', caption: gettext('Remove'), style: 'danger'}))
                }
            }
            else {
                throw new Error(gettext(`Peripheral ${this._peripheralId} could not be found`))
            }
        }.bind(this))
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
                    let peripheralsSection = this.getSection()
                    peripheralsSection.updatePeripheralsList()

                    this.close(/* force = */ true)

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to remove peripheral "${this._peripheralId}"`, error)
                    Utils.showToastError(error)

                }.bind(this))

            }.bind(this),
            pathId: 'remove'
        })
    }

}


export default PeripheralForm

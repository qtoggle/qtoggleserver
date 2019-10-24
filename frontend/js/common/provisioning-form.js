
import $      from '$qui/lib/jquery.module.js'
import Logger from '$qui/lib/logger.module.js'

import {gettext}                                from '$qui/base/i18n.js'
import {mix}                                    from '$qui/base/mixwith.js'
import {CheckField, TextField, PushButtonField} from '$qui/forms/common-fields.js'
import {PageForm}                               from '$qui/forms/common-forms.js'
import FormButton                               from '$qui/forms/form-button.js'
import FormField                                from '$qui/forms/form-field.js'
import {ValidationError}                        from '$qui/forms/forms.js'
import StockIcon                                from '$qui/icons/stock-icon.js'
import * as Toast                               from '$qui/messages/toast.js'
import * as PromiseUtils                        from '$qui/utils/promise.js'

import * as API                       from '$app/api.js'
import * as Cache                     from '$app/cache.js'
import * as Common                    from '$app/common/common.js'
import WaitDeviceMixin                from '$app/common/wait-device-mixin.js'
import * as StringUtils               from '$qui/utils/string.js'
import * as Messages                  from '$qui/messages/messages.js'
import {ConfirmMessageForm}           from '$qui/messages/common-message-forms.js'
import {TimeoutError, AssertionError} from '$qui/base/errors.js'


const GEAR_ICON = new StockIcon({name: 'gear'})

const logger = Logger.get('qtoggle.common.provisioning')


/**
 * @class QToggle.Common.ProvisioningForm
 * @extends qui.forms.PageForm
 * @param {String} deviceName
 */
export default class ProvisioningForm extends mix(PageForm).with(WaitDeviceMixin) {

    constructor(deviceName) {
        super({
            icon: GEAR_ICON,
            title: gettext('Device Provisioning'),
            pathId: 'provisioning',
            closeOnApply: false,
            continuousValidation: true,

            fields: [
                new PushButtonField({
                    name: 'factory_reset',
                    label: gettext('Factory Defaults'),
                    description: gettext('Reset device to factory defaults.'),
                    caption: gettext('Reset'),
                    style: 'danger',
                    callback: function (form) {
                        form.pushPage(form.confirmAndFactoryReset())
                    }
                })
            ],
            buttons: [
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true})
            ]
        })

        this._deviceName = deviceName
    }

    // load() {
        // if (this.deviceIsSlave()) {
        //     API.setSlave(this.getDeviceName())
        // }
        //
        // return this.fetchUpdateStatus().then(function (running) {
        //
        //     if (running) {
        //         /* Start polling, but do not chain it to load promise */
        //         this.pollStatus(POLLING_INTERVAL * 1000)
        //     }
        //
        // }.bind(this)).catch(function (error) {
        //
        //     logger.errorStack(`failed to get current firmware for device "${this.getDeviceName()}"`, error)
        //     this.setData({status: API.FIRMWARE_STATUS_ERROR})
        //
        //     PromiseUtils.asap().then(function () {
        //
        //         this.setError(error.toString())
        //
        //     }.bind(this))
        //
        // }.bind(this))
    // }

    getDeviceName() {
        return this._deviceName
    }

    deviceIsSlave() {
        return !Cache.isMainDevice(this.getDeviceName())
    }

    getDeviceAttrs() {
        if (this.deviceIsSlave()) {
            let device = Cache.getSlaveDevice(this.getDeviceName())
            if (!device) {
                throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
            }

            return device.attrs
        }
        else {
            return Cache.getMainDevice()
        }
    }

    confirmAndFactoryReset() {
        let attrs = this.getDeviceAttrs()
        let deviceDisplayName = attrs.display_name || attrs.name
        let deviceName = attrs.name

        let msg = StringUtils.formatPercent(
            gettext('Really reset device %(name)s to factory defaults?'),
            {name: Messages.wrapLabel(deviceDisplayName)}
        )

        return ConfirmMessageForm.show(
            msg,
            /* onYes = */ function () {

                logger.debug(`resetting device "${deviceName}" to factory defaults`)

                this.setProgress()

                if (this.deviceIsSlave()) {
                    API.setSlave(deviceName)
                }
                API.postReset(/* factory = */ true).then(function () {

                    logger.debug(`device "${deviceName}" is resetting to factory defaults`)
                    return PromiseUtils.withTimeout(this.waitDeviceOffline(), Common.GO_OFFLINE_TIMEOUT * 1000)

                }.bind(this)).then(function () {

                    logger.debug(`device "${deviceName}" went offline`)
                    this.clearProgress()
                    this.close()
                    Toast.info(gettext('Device has been reset.'))

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to reset device "${deviceName}" to factory defaults`, error)

                    if (error instanceof TimeoutError) {
                        error = new Error(gettext('Timeout waiting for device to disconnect.'))
                    }

                    this.cancelWaitingDevice()
                    this.setError(error.toString())

                }.bind(this)).then(function () {

                    this.clearProgress()

                }.bind(this))

            }.bind(this),
            /* onNo = */ null, /* pathId = */ 'factory-reset'
        )
    }

}


import {TimeoutError}       from '$qui/base/errors.js'
import {gettext}            from '$qui/base/i18n.js'
import {Mixin}              from '$qui/base/mixwith.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as Toast           from '$qui/messages/toast.js'
import * as PromiseUtils    from '$qui/utils/promise.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as BaseAPI    from '$app/api/base.js'
import * as DevicesAPI from '$app/api/devices.js'
import * as Cache      from '$app/cache.js'
import * as Common     from '$app/common/common.js'


/** @lends qtoggle.common.FactoryResetDeviceMixin */
const FactoryResetDeviceMixin = Mixin((superclass = Object) => {

    /**
     * A mixin to be used with device forms that allow factory reset.
     * @alias qtoggle.common.FactoryResetDeviceMixin
     * @mixin
     */
    class FactoryResetDeviceMixin extends superclass {

        /**
         * Do a factory reset on device after confirmation.
         * @param {String} deviceName the name of the device to reboot
         * @param {String} deviceDisplayName device display name
         * @param {Logger} logger
         * @returns {qui.pages.PageMixin}
         */
        confirmAndFactoryReset(deviceName, deviceDisplayName, logger) {
            let msg = StringUtils.formatPercent(
                gettext('Really reset device %(name)s to factory defaults?'),
                {name: Messages.wrapLabel(deviceDisplayName)}
            )

            return new ConfirmMessageForm({
                message: msg,
                onYes: function () {

                    logger.debug(`resetting device "${deviceName}" to factory defaults`)

                    this.setProgress()

                    if (!Cache.isMainDevice(deviceName)) {
                        BaseAPI.setSlaveName(deviceName)
                    }
                    DevicesAPI.postReset(/* factory = */ true).then(function () {

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

                        this.cancelWaiting()
                        this.setError(error)

                    }.bind(this)).then(function () {

                        this.clearProgress()

                    }.bind(this))

                }.bind(this),
                pathId: 'factory-reset'
            })
        }

    }

    return FactoryResetDeviceMixin

})


export default FactoryResetDeviceMixin

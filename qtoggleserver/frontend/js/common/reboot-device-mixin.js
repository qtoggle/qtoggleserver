
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


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/** @lends qtoggle.common.RebootDeviceMixin */
const RebootDeviceMixin = Mixin((superclass = Object) => {

    /**
     * A mixin to be used with device forms that allow rebooting.
     * @alias qtoggle.common.RebootDeviceMixin
     * @mixin
     */
    class RebootDeviceMixin extends superclass {

        /**
         * @constructs
         * @param {...*} args parent class parameters
         */
        constructor({...args} = {}) {
            super(args)

            this._rebooting = false
        }


        /**
         * Reboot a device after confirmation.
         * @param {String} deviceName the name of the device to reboot
         * @param {String} deviceDisplayName device display name
         * @param {Logger} logger
         * @returns {qui.pages.PageMixin}
         */
        confirmAndReboot(deviceName, deviceDisplayName, logger) {
            let msg = StringUtils.formatPercent(
                gettext('Really reboot device %(name)s?'),
                {name: Messages.wrapLabel(deviceDisplayName)}
            )

            return new ConfirmMessageForm({
                message: msg,
                onYes: () => this.doReboot(deviceName, logger),
                pathId: 'reboot'
            })
        }

        /**
         * Reboot device and wait for completion.
         * @param {String} deviceName the name of the device to reboot
         * @param {Logger} logger
         * @returns {qui.pages.PageMixin}
         */
        doReboot(deviceName, logger) {
            logger.debug(`rebooting device "${deviceName}"`)

            this.setProgress()
            this._rebooting = true

            /* Disable polling while rebooting */
            let polledDeviceName = Cache.getPolledDeviceName()
            if (polledDeviceName === deviceName) {
                Cache.setPolledDeviceName(null)
            }

            if (!Cache.isMainDevice(deviceName)) {
                BaseAPI.setSlaveName(deviceName)
            }
            DevicesAPI.postReset().then(function () {

                logger.debug(`device "${deviceName}" is rebooting`)
                return PromiseUtils.withTimeout(this.waitDeviceOffline(), Common.GO_OFFLINE_TIMEOUT * 1000)

            }.bind(this)).then(function () {

                return PromiseUtils.withTimeout(this.waitDeviceOnline(), Common.COME_ONLINE_TIMEOUT * 1000)

            }.bind(this)).then(function () {

                logger.debug(`device "${deviceName}" successfully rebooted`)
                this.clearProgress()
                Toast.info(gettext('Device has been rebooted.'))

            }.bind(this)).catch(function (error) {

                logger.errorStack(`failed to reboot device "${deviceName}"`, error)

                if (error instanceof TimeoutError) {
                    error.message = gettext('Timeout waiting for device to reconnect.')
                }

                this.cancelWaiting()
                this.setError(error)

            }.bind(this)).then(function () {

                this.clearProgress()
                this._rebooting = false

                /* Restore polling */
                if (polledDeviceName === deviceName) {
                    Cache.setPolledDeviceName(deviceName)
                }

            }.bind(this))
        }

        /**
         * Tell if the device is currently rebooting.
         * @returns {Boolean}
         */
        isRebooting() {
            return this._rebooting
        }

    }

    return RebootDeviceMixin

})


export default RebootDeviceMixin

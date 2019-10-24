import {TimeoutError}       from '$qui/base/errors.js'
import {gettext}            from '$qui/base/i18n.js'
import {Mixin}              from '$qui/base/mixwith.js'
import * as Cache           from '$app/cache.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as Toast           from '$qui/messages/toast.js'
import * as PromiseUtils    from '$qui/utils/promise.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as API    from '$app/api.js'
import * as Common from '$app/common/common.js'


export default Mixin((superclass = Object) => {

    class RebootFormMixin extends superclass {

        confirmAndReboot(deviceName, deviceDisplayName, logger) {
            let msg = StringUtils.formatPercent(
                gettext('Really reboot device %(name)s?'),
                {name: Messages.wrapLabel(deviceDisplayName)}
            )

            return ConfirmMessageForm.show(
                msg,
                /* onYes = */ function () {

                    logger.debug(`rebooting device "${deviceName}"`)

                    this.setProgress()

                    if (!Cache.isMainDevice(deviceName)) {
                        API.setSlave(deviceName)
                    }
                    API.postReset().then(function () {

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
                            error = new Error(gettext('Timeout waiting for device to reconnect.'))
                        }

                        this.cancelWaitingDevice()
                        this.setError(error.toString())

                    }.bind(this)).then(function () {

                        this.clearProgress()

                    }.bind(this))

                }.bind(this),
                /* onNo = */ null, /* pathId = */ 'reboot'
            )
        }

    }

    return RebootFormMixin

})

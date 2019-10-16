import ConditionVariable              from '$qui/base/condition-variable.js'
import {AssertionError, TimeoutError} from '$qui/base/errors.js'
import {gettext}                      from '$qui/base/i18n.js'
import {mix}                          from '$qui/base/mixwith.js'
import {
    CheckField, ComboField, PushButtonField,
    TextField
}                                     from '$qui/forms/common-fields.js'
import {PageForm}                     from '$qui/forms/common-forms.js'
import FormButton                     from '$qui/forms/form-button.js'
import {ConfirmMessageForm}           from '$qui/messages/common-message-forms.js'
import * as Messages                  from '$qui/messages/messages.js'
import * as Toast                     from '$qui/messages/toast.js'
import * as DateUtils                 from '$qui/utils/date.js'
import * as ObjectUtils               from '$qui/utils/object.js'
import * as PromiseUtils              from '$qui/utils/promise.js'
import * as StringUtils               from '$qui/utils/string.js'
import URL                            from '$qui/utils/url.js'

import * as API                                  from '$app/api.js'
import * as Cache                                from '$app/cache.js'
import {AttrdefFormMixin, preprocessDeviceAttrs} from '$app/common/common.js'
import UpdateFirmwareForm                        from '$app/common/update-firmware-form.js'

import * as Devices from './devices.js'


const MASTER_FIELDS = ['url', 'enabled', 'poll_interval', 'listen_enabled', 'last_sync']

const GO_OFFLINE_TIMEOUT = 20 /* Seconds */
const COME_ONLINE_TIMEOUT = 60 /* Seconds */


const logger = Devices.logger


/**
 * @class DeviceForm
 * @extends qui.forms.PageForm
 * @param {String} deviceName
 * @private
 */
export default class DeviceForm extends mix(PageForm).with(AttrdefFormMixin) {

    constructor(deviceName) {
        super({
            pathId: deviceName,
            keepPrevVisible: true,
            title: '',
            icon: Devices.DEVICE_ICON,
            closeOnApply: false,
            continuousValidation: true,

            fields: [
                new TextField({
                    name: 'url',
                    label: gettext('URL'),
                    readonly: true
                }),
                new CheckField({
                    name: 'enabled',
                    label: gettext('Enabled')
                }),
                new ComboField({
                    name: 'poll_interval',
                    label: gettext('Polling Interval'),
                    choices: Devices.POLL_CHOICES,
                    unit: gettext('seconds')
                }),
                new CheckField({
                    name: 'listen_enabled',
                    label: gettext('Enable Listening')
                }),
                new TextField({
                    name: 'last_sync',
                    label: gettext('Last Sync'),
                    readonly: true
                })
            ],
            buttons: [
                new FormButton({id: 'remove', caption: gettext('Remove'), style: 'danger'}),
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true})
            ]
        })

        this._fullAttrdefs = null
        this._deviceName = deviceName

        this._whenDeviceOnline = null
        this._whenDeviceOffline = null
        this._renamedDeviceNewName = null
    }

    init() {
        this.updateUI()
    }

    /**
     * Updates the entire form (fields & values) from the corresponding device.
     */
    updateUI() {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        device = ObjectUtils.copy(device, /* deep = */ true)
        device.url = new URL(device).toString()

        this._fullAttrdefs = null
        this._renamedDeviceNewName = null

        this.setTitle(device.attrs.description || device.name)
        this.setIcon(Devices.makeDeviceIcon(device))

        if (device.last_sync === 0) {
            device.last_sync = `(${gettext('never')})`
        }
        else {
            device.last_sync = DateUtils.formatPercent(new Date(device.last_sync * 1000), '%Y-%m-%d %H:%M:%S')
        }

        this.setData(device)

        if (device.enabled) {
            let attrdefs = ObjectUtils.copy(device.attrs.definitions || {}, /* deep = */ true)

            /* Merge in some additional attribute definitions that we happen to know of */
            ObjectUtils.forEach(API.ADDITIONAL_DEVICE_ATTRDEFS, function (name, def) {
                def = ObjectUtils.copy(def, /* deep = */ true)

                if (name in attrdefs) {
                    attrdefs[name] = ObjectUtils.combine(attrdefs[name], def)
                }
                else {
                    attrdefs[name] = def
                }
            })

            /* Combine standard and additional attribute definitions */
            this._fullAttrdefs = ObjectUtils.combine(API.STD_DEVICE_ATTRDEFS, attrdefs)

            /* Filter out attribute definitions not applicable to this device */
            this._fullAttrdefs = ObjectUtils.filter(this._fullAttrdefs, function (name, def) {
                let showAnyway = def.showAnyway
                if (typeof showAnyway === 'function') {
                    showAnyway = showAnyway(device.attrs, this._fullAttrdefs)
                }
                return def.common || showAnyway || name in device.attrs
            }, this)

            /* Make sure all defs have a valueToUI function */
            // TODO once AttrDef becomes a class, this will no longer be necessary */
            ObjectUtils.forEach(this._fullAttrdefs, function (name, def) {
                if (!def.valueToUI) {
                    def.valueToUI = function (value) {
                        return value
                    }
                }
            })

            this.fieldsFromAttrdefs(
                this._fullAttrdefs,
                /* extraFieldOptions = */ undefined,
                /* initialData = */ preprocessDeviceAttrs(device.attrs),
                /* provisioning = */ device.provisioning || []
            )
        }
        else {
            /* Clear all attribute fields */
            this.fieldsFromAttrdefs({})
        }

        this._addExtraFields(device)
    }

    getDeviceName() {
        return this._deviceName
    }

    setWaitingDeviceOnline() {
        if (this._whenDeviceOnline) {
            throw new AssertionError('Attempt to wait for device to come online while already waiting')
        }

        this.setProgress()

        this._whenDeviceOnline = new ConditionVariable()

        PromiseUtils.withTimeout(this._whenDeviceOnline, API.SERVER_TIMEOUT * 1000).catch(function (error) {

            if (error instanceof TimeoutError) {
                this.setError(gettext('Device is offline.'))
            }

            /* Other errors can practically only be generated by cancelling the condition variable */

        }.bind(this)).then(function () {

            this.clearProgress()

        }.bind(this))
    }

    clearWaitingDeviceOnline() {
        if (!this._whenDeviceOnline) {
            throw new AssertionError('Attempt to cancel waiting for device to come online while not waiting')
        }

        this.clearProgress()
        this._whenDeviceOnline.cancel()
        this._whenDeviceOnline = null
    }

    waitDeviceOnline() {
        if (this._whenDeviceOnline || this._whenDeviceOffline) {
            throw new AssertionError('Attempt to wait for device to come online while already waiting')
        }

        return (this._whenDeviceOnline = new ConditionVariable())
    }

    isWaitingDeviceOnline() {
        return !!this._whenDeviceOnline
    }

    isWaitingDeviceOffline() {
        return !!this._whenDeviceOffline
    }

    waitDeviceOffline() {
        if (this._whenDeviceOnline || this._whenDeviceOffline) {
            throw new AssertionError('Attempt to wait for device to go offline while already waiting')
        }

        return (this._whenDeviceOffline = new ConditionVariable())
    }

    fulfillDeviceOnline() {
        if (!this._whenDeviceOnline) {
            throw new AssertionError('Attempt to fulfill device online but not waiting')
        }

        this._whenDeviceOnline.fulfill()
        this._whenDeviceOnline = null
    }

    fulfillDeviceOffline() {
        if (!this._whenDeviceOffline) {
            throw new AssertionError('Attempt to fulfill device offline but not waiting')
        }

        this._whenDeviceOffline.fulfill()
        this._whenDeviceOffline = null
    }

    cancelWaitDevice() {
        if (this._whenDeviceOnline) {
            this._whenDeviceOnline.cancel()
            this._whenDeviceOnline = null
        }

        if (this._whenDeviceOffline) {
            this._whenDeviceOffline.cancel()
            this._whenDeviceOffline = null
        }
    }

    getRenamedDeviceNewName() {
        return this._renamedDeviceNewName
    }

    applyField(value, fieldName) {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        /* Always work on copy */
        device = ObjectUtils.copy(device, /* deep = */ true)

        // TODO use device.isPermanentlyOffline()
        let devicePermanentlyOffline = device.poll_interval === 0 && !device.listen_enabled

        let deviceName = this.getDeviceName()

        if (MASTER_FIELDS.indexOf(fieldName) >= 0) {
            logger.debug(`updating device master property "${deviceName}.{fieldName}" to ${JSON.stringify(value)}`)
            device[fieldName] = value

            if (fieldName === 'enabled' && value && !devicePermanentlyOffline) {
                this.setWaitingDeviceOnline()
            }

            return API.patchSlaveDevice(
                deviceName,
                device.enabled,
                device.poll_interval,
                device.listen_enabled
            ).then(function () {

                logger.debug(`device master property "${deviceName}.${fieldName}" successfully updated`)

            }).catch(function (error) {

                logger.errorStack(`failed to update device master property "${deviceName}.${fieldName}"`, error)
                if (this.isWaitingDeviceOnline()) {
                    this.clearWaitingDeviceOnline()
                }

                throw error

            }.bind(this))
        }
        else { /* A slave device attribute was updated */
            if (!this._fullAttrdefs) {
                return /* Device offline */
            }

            let name = fieldName.substring(5)
            if (!(name in this._fullAttrdefs) || !this._fullAttrdefs[name].modifiable) {
                return
            }

            logger.debug(`updating device attribute "${deviceName}.${name}" to ${JSON.stringify(value)}`)

            let newAttrs = {}
            newAttrs[name] = value

            if (name === 'name') {
                /* Device renamed, remember new name for reopening */
                this._renamedDeviceNewName = value
            }

            API.setSlave(deviceName)
            return API.patchDevice(newAttrs).then(function () {

                logger.debug(`device attribute "${deviceName}.${name}" successfully updated`)

            }).catch(function (error) {

                logger.errorStack(`failed to update device attribute "${deviceName}.${name}"`, error)
                throw error

            }).then(function () {

                if (!this._fullAttrdefs[name].reconnect) {
                    return
                }

                /* Attributes with reconnect flag will probably restart/reset the device
                 * therefore we first wait for it to go offline and then to come back online */

                this.setProgress()

                /* Following promise chain is intentionally not part of the outer chain,
                 * because by the time it resolves, the field will no longer be part of the DOM */
                Promise.resolve().then(function () {

                    return PromiseUtils.withTimeout(this.waitDeviceOffline(), GO_OFFLINE_TIMEOUT * 1000)

                }.bind(this)).then(function () {

                    return PromiseUtils.withTimeout(this.waitDeviceOnline(), COME_ONLINE_TIMEOUT * 1000)

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to set device attribute "${deviceName}.${fieldName}"`, error)

                    if (error instanceof TimeoutError) {
                        error = new Error(gettext('Timeout waiting for device to reconnect.'))
                        this.cancelWaitDevice()
                    }

                    this.setError(error.toString())

                }.bind(this)).then(function () {

                    this.clearProgress()

                }.bind(this))

            }.bind(this))
        }
    }

    onClose() {
        this._renamedDeviceNewName = null
        this.cancelWaitDevice()
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'remove':
                this.pushPage(this.makeRemoveDeviceForm())

                break
        }
    }

    _addExtraFields(device) {
        /* Update firmware button */
        if (this.getField('update_firmware')) {
            this.removeField('update_firmware')
        }

        if (device.online && device.attrs.flags.indexOf('firmware') >= 0) {
            this.addField(-1, new PushButtonField({
                name: 'update_firmware',
                label: gettext('Update Firmware'),
                separator: true,
                caption: gettext('Check'),
                callback(form) {
                    form.pushPage(form.makeUpdateFirmwareForm())
                }
            }))
        }
    }

    navigate(pathId) {
        switch (pathId) {
            case 'remove':
                return this.makeRemoveDeviceForm()

            case 'firmware':
                return this.makeUpdateFirmwareForm()
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeRemoveDeviceForm() {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        let msg = StringUtils.formatPercent(
            gettext('Really remove %(object)s?'),
            {object: Messages.wrapLabel(device.attrs.description || device.name)}
        )

        return ConfirmMessageForm.show(
            msg,
            /* onYes = */ function () {

                logger.debug(`removing device "${device.name}" at url ${device.url}`)

                API.deleteSlaveDevice(device.name).then(function () {

                    logger.debug(`device "${device.name}" at url ${device.url} successfully removed`)
                    this.close()

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to remove device "${device.name}" at url ${device.url}`, error)
                    Toast.error(error.toString())

                })

            }.bind(this),
            /* onNo = */ null, /* pathId = */ 'remove'
        )
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeUpdateFirmwareForm() {
        return new UpdateFirmwareForm(this.getDeviceName())
    }

}

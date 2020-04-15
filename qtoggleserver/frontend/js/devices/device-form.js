
import {AssertionError}           from '$qui/base/errors.js'
import {TimeoutError}             from '$qui/base/errors.js'
import {gettext}                  from '$qui/base/i18n.js'
import {mix}                      from '$qui/base/mixwith.js'
import Timer                      from '$qui/base/timer.js'
import {CheckField}               from '$qui/forms/common-fields.js'
import {ComboField}               from '$qui/forms/common-fields.js'
import {PushButtonField}          from '$qui/forms/common-fields.js'
import {TextField}                from '$qui/forms/common-fields.js'
import {CompositeField}           from '$qui/forms/common-fields.js'
import {PageForm}                 from '$qui/forms/common-forms.js'
import FormButton                 from '$qui/forms/form-button.js'
import {ConfirmMessageForm}       from '$qui/messages/common-message-forms.js'
import {StickyConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Messages              from '$qui/messages/messages.js'
import * as Toast                 from '$qui/messages/toast.js'
import * as Theme                 from '$qui/theme.js'
import * as DateUtils             from '$qui/utils/date.js'
import * as ObjectUtils           from '$qui/utils/object.js'
import * as PromiseUtils          from '$qui/utils/promise.js'
import * as StringUtils           from '$qui/utils/string.js'
import URL                        from '$qui/utils/url.js'
import * as Window                from '$qui/window.js'

import * as Attrdefs         from '$app/api/attrdefs.js'
import * as BaseAPI          from '$app/api/base.js'
import * as DevicesAPI       from '$app/api/devices.js'
import * as MasterSlaveAPI   from '$app/api/master-slave.js'
import * as NotificationsAPI from '$app/api/notifications.js'
import * as Cache            from '$app/cache.js'
import AttrdefFormMixin      from '$app/common/attrdef-form-mixin.js'
import * as Common           from '$app/common/common.js'
import ProvisioningForm      from '$app/common/provisioning-form.js'
import RebootDeviceMixin     from '$app/common/reboot-device-mixin.js'
import UpdateFirmwareForm    from '$app/common/update-firmware-form.js'
import WaitDeviceMixin       from '$app/common/wait-device-mixin.js'

import * as Devices from './devices.js'


const MASTER_FIELDS = ['url', 'enabled', 'poll_interval', 'listen_enabled', 'last_sync']

const logger = Devices.logger


function getDeviceURL(device) {
    // TODO make this function a method of Device class, once we have a Device class in place
    return new URL(device).toString()
}


/**
 * @alias qtoggle.devices.DeviceForm
 * @extends qui.forms.PageForm
 * @mixes qtoggle.common.AttrdefFormMixin
 * @mixes qtoggle.common.WaitDeviceMixin
 * @mixes qtoggle.common.RebootDeviceMixin
 */
class DeviceForm extends mix(PageForm).with(AttrdefFormMixin, WaitDeviceMixin, RebootDeviceMixin) {

    /**
     * @constructs
     * @param {String} deviceName
     */
    constructor(deviceName) {
        super({
            pathId: deviceName,
            keepPrevVisible: true,
            title: '',
            icon: Devices.DEVICE_ICON,
            closeOnApply: false,
            preventUnappliedClose: true,

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
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true}),
                new FormButton({id: 'apply', caption: gettext('Apply'), def: true})
            ]
        })

        this._fullAttrdefs = null
        this._deviceName = deviceName
        this._staticFieldsAdded = false
        this._deviceRemoved = false

        this._updateTimeFieldsTimer = new Timer(
            /* defaultTimeout = */ 1000,
            () => this.updateTimeFields(),
            /* repeat = */ true
        )

        Devices.setRenamedDeviceName(null)
    }

    init() {
        this.updateUI(/* fieldChangeWarnings = */ false)
    }

    load() {
        /* Explicitly query attributes that don't normally generate events, directly from the slave device */
        BaseAPI.setSlaveName(this.getDeviceName())
        return DevicesAPI.getDevice().then(function (attrs) {
            attrs = ObjectUtils.filter(attrs, n => (NotificationsAPI.NO_EVENT_DEVICE_ATTRS.indexOf(n) >= 0))
            attrs = ObjectUtils.mapKey(attrs, n => `attr_${n}`)
            this.setData(attrs)
        }.bind(this))
    }

    onBecomeCurrent() {
        if (this._deviceRemoved) {
            return
        }

        if (!this._updateTimeFieldsTimer.isRunning()) {
            this._updateTimeFieldsTimer.start()
        }

        Cache.setPolledDeviceName(this.getDeviceName())
    }

    onLeaveCurrent() {
        if (this._updateTimeFieldsTimer.isRunning()) {
            this._updateTimeFieldsTimer.cancel()
        }

        Cache.setPolledDeviceName(null)
    }

    /**
     * Update the entire form (fields & values) from the corresponding device.
     */
    updateUI(fieldChangeWarnings = true) {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        device = ObjectUtils.copy(device, /* deep = */ true)
        device.url = getDeviceURL(device)

        this._fullAttrdefs = null

        this.setTitle(device.attrs.display_name || device.name)
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
            ObjectUtils.forEach(Attrdefs.ADDITIONAL_DEVICE_ATTRDEFS, function (name, def) {
                def = ObjectUtils.copy(def, /* deep = */ true)

                if (name in attrdefs) {
                    attrdefs[name] = ObjectUtils.combine(attrdefs[name], def)
                }
                else {
                    attrdefs[name] = def
                }
            })

            /* Combine standard and additional attribute definitions */
            this._fullAttrdefs = Common.combineAttrdefs(Attrdefs.STD_DEVICE_ATTRDEFS, attrdefs)

            /* Filter out attribute definitions not applicable to this device */
            this._fullAttrdefs = ObjectUtils.filter(this._fullAttrdefs, function (name, def) {
                let showAnyway = def.showAnyway
                if (typeof showAnyway === 'function') {
                    showAnyway = showAnyway(device.attrs, this._fullAttrdefs)
                }
                return def.common || showAnyway || name in device.attrs
            }, this)

            this.fieldsFromAttrdefs({
                attrdefs: this._fullAttrdefs,
                initialData: Common.preprocessDeviceAttrs(device.attrs),
                provisioning: device.provisioning || [],
                noUpdated: NotificationsAPI.NO_EVENT_DEVICE_ATTRS,
                startIndex: this.getFieldIndex('last_sync') + 1,
                fieldChangeWarnings: fieldChangeWarnings
            })
        }
        else {
            /* Clear all attribute fields */
            this.fieldsFromAttrdefs()
        }

        if (!this._staticFieldsAdded) {
            this.addStaticFields()
            this._staticFieldsAdded = true
        }

        this.updateStaticFields(device.attrs)
    }

    /**
     * Add fields whose presence is not altered by device attributes.
     */
    addStaticFields() {
        this.addField(-1, new CompositeField({
            name: 'management_buttons',
            label: gettext('Manage Device'),
            separator: true,
            layout: Window.isSmallScreen() ? 'vertical' : 'horizontal',
            fields: [
                new PushButtonField({
                    name: 'reboot',
                    separator: true,
                    caption: gettext('Reboot'),
                    style: 'highlight',
                    onClick(form) {
                        form.pushPage(form.makeConfirmAndRebootForm())
                    }
                }),
                new PushButtonField({
                    name: 'provision',
                    style: 'interactive',
                    caption: gettext('Provision'),
                    onClick(form) {
                        form.pushPage(form.makeProvisioningForm())
                    }
                }),
                new PushButtonField({
                    name: 'firmware',
                    style: 'colored',
                    backgroundColor: Theme.getColor('@magenta-color'),
                    backgroundActiveColor: Theme.getColor('@magenta-active-color'),
                    caption: gettext('Firmware'),
                    disabled: true,
                    onClick(form) {
                        form.pushPage(form.makeUpdateFirmwareForm())
                    }
                })
            ]
        }))
    }

    /**
     * Enable/disable static fields based on device attributes.
     * @param {Object} attrs device attributes
     */
    updateStaticFields(attrs) {
        let updateFirmwareButtonField = this.getField('management_buttons').getField('firmware')
        if (attrs.flags.indexOf('firmware') >= 0) {
            updateFirmwareButtonField.enable()
        }
        else {
            updateFirmwareButtonField.disable()
        }
    }

    /**
     * Update the values of attributes depending on time. Called every second, when form is visible.
     */
    updateTimeFields() {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        let attrs = device.attrs

        let field = this.getField('attr_date')
        if (field && attrs['date'] != null && !field.isFocused() && !field.isChanged()) {
            let value = Attrdefs.STD_DEVICE_ATTRDEFS['date'].valueToUI(attrs['date'])
            field.setValue(value)
        }

        field = this.getField('attr_uptime')
        if (field && attrs['uptime'] != null) {
            field.setValue(attrs['uptime'])
        }
    }

    /**
     * @returns {String}
     */
    getDeviceName() {
        return this._deviceName
    }

    /**
     * Start waiting for device to come line.
     */
    startWaitingDeviceOnline() {
        this.setProgress()

        PromiseUtils.withTimeout(
            this.waitDeviceOnline(),
            BaseAPI.DEFAULT_SERVER_TIMEOUT * 1000
        ).catch(function (error) {

            if (error instanceof TimeoutError) {
                this.setError(gettext('Device is offline.'))
            }

            /* Other errors can practically only be generated by cancelling the condition variable */

        }.bind(this)).then(function () {

            this.clearProgress()

        }.bind(this))
    }

    applyData(data) {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        // TODO use device.isPermanentlyOffline()
        let devicePermanentlyOffline = device.poll_interval === 0 && !device.listen_enabled
        let deviceName = this.getDeviceName()

        let newAttrs = {}
        let masterAttrsChanged = false
        let changedFields = this.getChangedFieldNames()
        let justEnabled = false
        let willReconnect = false

        changedFields.forEach(function (fieldName) {
            let value = data[fieldName]
            if (value == null) {
                return
            }

            if (MASTER_FIELDS.indexOf(fieldName) >= 0) {
                logger.debug(`updating device "${deviceName}" master attribute ` +
                             `${fieldName}" to ${JSON.stringify(value)}`)
                masterAttrsChanged = true

                if (fieldName === 'enabled' && value && !devicePermanentlyOffline) {
                    logger.debug(`device "${deviceName}" has just been enabled`)
                    justEnabled = true
                }

                /* Clear out field warning */
                this.getField(fieldName).clearWarning()

            }
            else if (fieldName.startsWith('attr_')) {
                let name = fieldName.substring(5)
                let def = this._fullAttrdefs[name]

                /* Ignore non-modifiable or undefined attributes */
                if (!def || !def.modifiable) {
                    return
                }

                if (def.valueFromUI) {
                    value = def.valueFromUI(value)
                }

                /* Clear out field warning */
                this.getField(fieldName).clearWarning()

                logger.debug(`updating device "${deviceName}" attribute "${name}" to ${JSON.stringify(value)}`)
                newAttrs[name] = value

                if (name === 'name') {
                    /* Device renamed, remember new name for reopening */
                    logger.debug(`device "${deviceName}" renamed to "${value}"`)
                    Devices.setRenamedDeviceName(value)
                }

                if (this._fullAttrdefs[name].reconnect) {
                    willReconnect = true
                }
            }
            else {
                logger.warn(`unknown device form field ${fieldName}`)
            }

        }, this)

        if (willReconnect) {
            logger.debug(`device "${deviceName}" will reconnect`)
        }

        let promise = Promise.resolve()

        if ('name' in newAttrs) {
            let msg = gettext('Are you sure you want to rename the device?')
            promise = new StickyConfirmMessageForm({message: msg}).show().asPromise()
        }

        if (willReconnect) {
            let msg = gettext('Device will reconnect. Are you sure?')
            promise = new StickyConfirmMessageForm({message: msg}).show().asPromise()
        }

        if (masterAttrsChanged) {
            promise = promise.then(function () {

                return MasterSlaveAPI.patchSlaveDevice(
                    deviceName,
                    data.enabled,
                    data.poll_interval,
                    data.listen_enabled
                ).then(function () {

                    logger.debug(`device "${deviceName}" master properties successfully updated for`)

                    if (justEnabled) {
                        this.startWaitingDeviceOnline()
                    }

                    Devices.recentDeviceUpdateTimer.restart()

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to update device "${deviceName}" master properties`, error)

                    this.cancelWaiting()

                    throw error

                }.bind(this))

            }.bind(this))
        }

        if (this._fullAttrdefs && Object.keys(newAttrs).length) { /* Device online */
            promise = promise.then(function () {

                BaseAPI.setSlaveName(deviceName)
                return DevicesAPI.patchDevice(newAttrs).then(function () {

                    logger.debug(`device "${deviceName}" attributes successfully updated`)
                    Devices.recentDeviceUpdateTimer.restart()

                }).catch(function (error) {

                    logger.errorStack(`failed to update device "${deviceName}" attributes`, error)
                    throw error

                }).then(function () {

                    /* Attributes with reconnect flag will probably restart/reset the device, therefore we first wait
                     * for it to go offline and then to come back online */

                    if (!willReconnect) {
                        return
                    }

                    this.setProgress()

                    /* Following promise chain is intentionally not part of the outer chain, because by the time it
                     * resolves, the field will no longer be part of the DOM */
                    return Promise.resolve().then(function () {

                        return PromiseUtils.withTimeout(this.waitDeviceOffline(), Common.GO_OFFLINE_TIMEOUT * 1000)

                    }.bind(this)).then(function () {

                        return PromiseUtils.withTimeout(this.waitDeviceOnline(), Common.COME_ONLINE_TIMEOUT * 1000)

                    }.bind(this)).catch(function (error) {

                        logger.errorStack(`error while waiting for device "${deviceName}" to come online`, error)

                        if (error instanceof TimeoutError) {
                            error = new Error(gettext('Timeout waiting for device to reconnect.'))
                        }

                        this.cancelWaiting()
                        this.setError(error)

                    }.bind(this)).then(function () {

                        this.clearProgress()

                    }.bind(this))

                }.bind(this))

            }.bind(this))
        }

        return promise
    }

    onPush() {
        Devices.setCurrentDeviceName(this._deviceName)
    }

    onClose() {
        Devices.setCurrentDeviceName(null)
        this.cancelWaiting()
    }

    onButtonPress(button) {
        switch (button.getId()) {
            case 'remove':
                this.pushPage(this.makeRemoveDeviceForm())

                break
        }
    }

    navigate(pathId) {
        switch (pathId) {
            case 'remove':
                return this.makeRemoveDeviceForm()

            case 'firmware':
                return this.makeUpdateFirmwareForm()

            case 'provisioning':
                return this.makeProvisioningForm()

            case 'reboot':
                return this.makeConfirmAndRebootForm()
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

        let deviceURL = getDeviceURL(device)

        let msg = StringUtils.formatPercent(
            gettext('Really remove %(object)s?'),
            {object: Messages.wrapLabel(device.attrs.display_name || device.name)}
        )

        return new ConfirmMessageForm({
            message: msg,
            onYes: function () {

                logger.debug(`removing device "${device.name}" at url ${deviceURL}`)
                this._deviceRemoved = true

                MasterSlaveAPI.deleteSlaveDevice(device.name).then(function () {

                    logger.debug(`device "${device.name}" at url ${deviceURL} successfully removed`)

                }.bind(this)).catch(function (error) {

                    logger.errorStack(`failed to remove device "${device.name}" at url ${deviceURL}`, error)
                    Toast.error(error.message)

                })

            }.bind(this),
            pathId: 'remove'
        })
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeUpdateFirmwareForm() {
        return new UpdateFirmwareForm(this.getDeviceName())
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeProvisioningForm() {
        return new ProvisioningForm(this.getDeviceName())
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeConfirmAndRebootForm() {
        let device = Cache.getSlaveDevice(this.getDeviceName())
        if (!device) {
            throw new AssertionError(`Device with name ${this.getDeviceName()} not found in cache`)
        }

        let displayName = device.display_name || device.name

        return this.confirmAndReboot(device.name, displayName, logger)
    }

}


export default DeviceForm

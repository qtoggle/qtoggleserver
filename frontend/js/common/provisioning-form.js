
import Logger from '$qui/lib/logger.module.js'

import {gettext}                     from '$qui/base/i18n.js'
import {mix}                         from '$qui/base/mixwith.js'
import {PushButtonField, ComboField} from '$qui/forms/common-fields.js'
import {PageForm}                    from '$qui/forms/common-forms.js'
import FormButton                    from '$qui/forms/form-button.js'
import StockIcon                     from '$qui/icons/stock-icon.js'
import * as Toast                    from '$qui/messages/toast.js'
import * as ArrayUtils               from '$qui/utils/array.js'
import * as PromiseUtils             from '$qui/utils/promise.js'

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
                }),
                new ComboField({
                    name: 'default_config',
                    label: gettext('Default Configuration'),
                    separator: true,
                    description: gettext('Apply a default configuration specific to this device model.'),
                    choices: [
                        {value: 'sonoff-touch/1-channel', label: 'sonoff-touch/1-channel'}
                    ]
                }),
                new PushButtonField({
                    name: 'apply_default_config',
                    label: ' ',
                    style: 'interactive',
                    caption: gettext('Apply'),
                    callback: function (form) {
                    }
                })
                /* new ComboField({
                    name: 'backup_config',
                    label: gettext('Backup Configuration'),
                    separator: true,
                    description: gettext('Manage backup configurations for this device.'),
                    choices: [
                        {value: 'sonoff-touch/1-channel', label: 'sonoff-touch/1-channel'}
                    ]
                }),
                new CompositeField({
                    name: 'backup_buttons1',
                    label: ' ',
                    layout: Window.isSmallScreen() ? 'vertical' : 'horizontal',
                    fields: [
                        new PushButtonField({
                            name: 'restore',
                            style: 'highlight',
                            caption: gettext('Restore'),
                            callback(form) {
                            }
                        }),
                        new PushButtonField({
                            name: 'create',
                            caption: gettext('Create'),
                            style: 'interactive',
                            callback(form) {
                            }
                        }),
                        new PushButtonField({
                            name: 'delete',
                            style: 'interactive',
                            caption: gettext('Delete'),
                            callback(form) {
                            }
                        })
                    ]
                }),
                new CompositeField({
                    name: 'backup_buttons2',
                    label: ' ',
                    layout: Window.isSmallScreen() ? 'vertical' : 'horizontal',
                    fields: [
                        new PushButtonField({
                            name: 'download',
                            style: 'interactive',
                            caption: gettext('Download'),
                            callback(form) {
                            }
                        }),
                        new PushButtonField({
                            name: 'upload',
                            caption: gettext('Upload'),
                            style: 'interactive',
                            callback(form) {
                            }
                        })
                    ]
                }) */
            ],
            buttons: [
                new FormButton({id: 'close', caption: gettext('Close'), cancel: true})
            ]
        })

        this._deviceName = deviceName
    }

    load() {
        let deviceAttrs = this.getDeviceAttrs()

        return API.getProvisioningConfigs(deviceAttrs.config_name || '').then(function (configs) {

            let choices = ArrayUtils.sortKey(configs, c => c.name).map(c => ({value: c.name, label: c.name}))
            let field = this.getField('default_config')
            field.setChoices(choices)

            if (choices.length) {
                this.setData({default_config: choices[0].value})
            }

        }.bind(this)).catch(function () {

            logger.error('failed to get provisioning configurations')
            this.setError(gettext('Failed to get provisioning configurations.'))

        }.bind(this))
    }

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

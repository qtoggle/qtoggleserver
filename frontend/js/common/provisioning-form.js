
import Logger from '$qui/lib/logger.module.js'

import {TimeoutError}       from '$qui/base/errors.js'
import {AssertionError}     from '$qui/base/errors.js'
import {gettext}            from '$qui/base/i18n.js'
import {mix}                from '$qui/base/mixwith.js'
import {PushButtonField}    from '$qui/forms/common-fields.js'
import {ComboField}         from '$qui/forms/common-fields.js'
import {PageForm}           from '$qui/forms/common-forms.js'
import FormButton           from '$qui/forms/form-button.js'
import StockIcon            from '$qui/icons/stock-icon.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Messages        from '$qui/messages/messages.js'
import * as Toast           from '$qui/messages/toast.js'
import {ModalProgressPage}  from '$qui/pages/common-pages.js'
import * as ArrayUtils      from '$qui/utils/array.js'
import * as PromiseUtils    from '$qui/utils/promise.js'
import * as StringUtils     from '$qui/utils/string.js'

import * as API           from '$app/api.js'
import * as Cache         from '$app/cache.js'
import * as BackupRestore from '$app/common/backup-restore.js'
import * as Common        from '$app/common/common.js'
import WaitDeviceMixin    from '$app/common/wait-device-mixin.js'


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
                        form.clearError()
                        form.pushPage(form.confirmAndFactoryReset())
                    }
                }),
                new ComboField({
                    name: 'default_config',
                    label: gettext('Default Configuration'),
                    separator: true,
                    description: gettext('Apply a default configuration specific to this device model.'),
                    choices: []
                }),
                new PushButtonField({
                    name: 'apply_default_config',
                    label: ' ',
                    style: 'interactive',
                    disabled: true,
                    caption: gettext('Apply'),
                    callback: function (form) {
                        form.clearError()
                        form.applyDefaultConfig()
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

        if (!deviceAttrs['config_name']) {
            this.getField('default_config').hide()
            this.getField('apply_default_config').hide()

            return Promise.resolve()
        }

        return API.getProvisioningConfigs(deviceAttrs.config_name || '').then(function (configs) {

            let choices = ArrayUtils.sortKey(configs, c => c.name).map(c => ({value: c.name, label: c.name}))
            let field = this.getField('default_config')
            field.setChoices(choices)

            if (choices.length) {
                this.setData({default_config: choices[0].value})
                this.getField('apply_default_config').enable()
            }

        }.bind(this)).catch(function (error) {

            logger.error(`failed to get provisioning configurations: ${error}`)
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

    applyDefaultConfig() {
        this.getData().then(function (data) {
            let configName = data['default_config']
            let modalProgress = new ModalProgressPage()
            let slaveName = this.deviceIsSlave() ? this.getDeviceName() : null

            modalProgress.setMessage(gettext('Fetching configuration file'))
            modalProgress.setProgressPercent(-1)
            this.pushPage(modalProgress)

            API.getProvisioningConfig(configName).then(function (config) {

                return BackupRestore.applyDefaultConfig(slaveName, config, modalProgress)

            }).catch(function (error) {

                this.setError(error)

            }.bind(this)).then(function () {

                modalProgress.close()

            })

        }.bind(this))
    }

    confirmAndFactoryReset() {
        let attrs = this.getDeviceAttrs()
        let deviceDisplayName = attrs.display_name || attrs.name
        let deviceName = attrs.name

        let msg = StringUtils.formatPercent(
            gettext('Really reset device %(name)s to factory defaults?'),
            {name: Messages.wrapLabel(deviceDisplayName)}
        )

        return new ConfirmMessageForm({
            message: msg,
            onYes: function () {

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
                    this.setError(error)

                }.bind(this)).then(function () {

                    this.clearProgress()

                }.bind(this))

            }.bind(this),
            pathId: 'factory-reset'
        })
    }

}

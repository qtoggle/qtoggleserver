
import {gettext}            from '$qui/base/i18n.js'
import {mix}                from '$qui/base/mixwith.js'
import Config               from '$qui/config.js'
import {CheckField}         from '$qui/forms/common-fields.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields.js'
import {CompositeField}     from '$qui/forms/common-fields.js'
import {PushButtonField}    from '$qui/forms/common-fields.js'
import {SliderField}        from '$qui/forms/common-fields.js'
import {TextField}          from '$qui/forms/common-fields.js'
import {PageForm}           from '$qui/forms/common-forms.js'
import {ErrorMapping}       from '$qui/forms/forms.js'
import {ValidationError}    from '$qui/forms/forms.js'
import FormButton           from '$qui/forms/form-button.js'
import {ConfirmMessageForm} from '$qui/messages/common-message-forms.js'
import * as Toast           from '$qui/messages/toast.js'
import * as Navigation      from '$qui/navigation.js'
import * as Theme           from '$qui/theme.js'
import * as ObjectUtils     from '$qui/utils/object.js'
import * as Window          from '$qui/window.js'

import * as Attrdefs         from '$app/api/attrdefs.js'
import * as AuthAPI          from '$app/api/auth.js'
import * as BaseAPI          from '$app/api/base.js'
import * as DevicesAPI       from '$app/api/devices.js'
import * as NotificationsAPI from '$app/api/notifications.js'
import * as Cache            from '$app/cache.js'
import AttrdefFormMixin      from '$app/common/attrdef-form-mixin.js'
import * as Common           from '$app/common/common.js'
import ProvisioningForm      from '$app/common/provisioning-form.js'
import RebootDeviceMixin     from '$app/common/reboot-device-mixin.js'
import UpdateFirmwareForm    from '$app/common/update-firmware-form.js'
import WaitDeviceMixin       from '$app/common/wait-device-mixin.js'

import * as ClientSettings from './client-settings.js'
import * as Settings       from './settings.js'


const logger = Settings.logger


/**
 * @alias qtoggle.settings.SettingsForm
 * @extends qui.forms.PageForm
 * @mixes qtoggle.common.AttrdefFormMixin
 * @mixes qtoggle.common.WaitDeviceMixin
 * @mixes qtoggle.common.RebootDeviceMixin
 */
class SettingsForm extends mix(PageForm).with(AttrdefFormMixin, WaitDeviceMixin, RebootDeviceMixin) {

    /**
     * @constructs
     */
    constructor() {
        super({
            title: gettext('Settings'),
            icon: Settings.WRENCH_ICON,
            closeOnApply: false,
            preventUnappliedClose: true,

            buttons: [
                new FormButton({id: 'apply', caption: gettext('Apply'), def: true, style: 'interactive'})
            ]
        })

        this._fullAttrdefs = null
        this._staticFieldsAdded = false
    }

    init() {
        this.updateUI(/* fieldChangeWarnings = */ false)

        this.setData({
            theme: ClientSettings.getTheme(),
            disable_effects: ClientSettings.isEffectsDisabled(),
            mobile_screen_mode: ClientSettings.getMobileScreenMode(),
            scaling_factor: ClientSettings.getScalingFactor()
        })
    }

    onBecomeCurrent() {
        Cache.setPolledDeviceName('')
    }

    onLeaveCurrent() {
        Cache.setPolledDeviceName(null)
    }

    /**
     * Updates the entire form (fields & values) from cached device attributes.
     */
    updateUI(fieldChangeWarnings = true) {
        /* Work on copy */
        let attrs = Cache.getMainDevice()
        let attrdefs = ObjectUtils.copy(attrs.definitions, /* deep = */ true)

        this.clearProgress()

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
                showAnyway = showAnyway(attrs, this._fullAttrdefs)
            }
            return def.common || showAnyway || name in attrs

        }, this)

        /* We don't want a separator over the first field, which is "name" */
        this._fullAttrdefs['name'].separator = false

        this.fieldsFromAttrdefs({
            attrdefs: this._fullAttrdefs,
            initialData: Common.preprocessDeviceAttrs(attrs),
            noUpdated: NotificationsAPI.NO_EVENT_DEVICE_ATTRS,
            fieldChangeWarnings: fieldChangeWarnings
        })

        if (!this._staticFieldsAdded) {
            this.addStaticFields()
            this._staticFieldsAdded = true
        }

        this.updateStaticFields(attrs)
    }

    /**
     * Add fields whose presence is not altered by device attributes.
     */
    addStaticFields() {
        this.addField(this.getFieldIndex('attr_version'), new TextField({
            name: 'app_version',
            label: gettext('App Version'),
            description: gettext('Currently running application version.'),
            readonly: true,
            initialValue: Config.appCurrentVersion
        }))

        this.addField(-1, new ChoiceButtonsField({
            name: 'theme',
            label: gettext('Theme'),
            description: gettext('Select the desired UI theme.'),
            separator: true,
            choices: Object.entries(Theme.getAvailable()).map(function ([value, label]) {
                return {value: value, label: label}
            })
        }))

        this.addField(-1, new ChoiceButtonsField({
            name: 'mobile_screen_mode',
            label: gettext('Mobile Screen Mode'),
            description: gettext('Choose how the app detects whether it runs on a mobile (small) screen or not.'),
            choices: [
                {value: 'auto', label: gettext('Auto')},
                {value: 'always', label: gettext('Always')},
                {value: 'never', label: gettext('Never')}
            ]
        }))

        this.addField(-1, new SliderField({
            name: 'scaling_factor',
            label: gettext('UI Scaling Factor'),
            description: gettext('Increase or decrease the size of the UI elements.'),
            ticks: [
                {value: 0.5, label: '50%'},
                {value: 0.75, label: '75%'},
                {value: 1, label: '100%'},
                {value: 1.25, label: '125%'},
                {value: 1.5, label: '150%'},
                {value: 2, label: '200%'}
            ],
            equidistant: true
        }))

        this.addField(-1, new CheckField({
            name: 'disable_effects',
            label: gettext('Disable Effects'),
            description: gettext('Use this option on slow devices to disable animations and other visual effects.')
        }))

        let managementButtons = [
            new PushButtonField({
                name: 'reboot',
                separator: true,
                caption: gettext('Reboot'),
                style: 'danger',
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

        if (Config.slavesEnabled) {
            managementButtons.push(
                new PushButtonField({
                    name: 'ports',
                    style: 'interactive',
                    caption: gettext('Ports'),
                    onClick(form) {
                        Navigation.navigate(['ports', Cache.getMainDevice().name])
                    }
                })
            )
        }

        this.addField(-1, new CompositeField({
            name: 'management_buttons',
            label: gettext('Manage Device'),
            separator: true,
            flow: Window.isSmallScreen() ? 'vertical' : 'horizontal',
            columns: 3,
            fields: managementButtons
        }))
    }

    /**
     * Enable/disable static fields based on device attributes.
     * @param {Object} attrs device attributes
     */
    updateStaticFields(attrs) {
        let updateFirmwareButtonField = this.getField('management_buttons').getField('firmware')
        if (attrs.flags.includes('firmware')) {
            updateFirmwareButtonField.enable()
        }
        else {
            updateFirmwareButtonField.disable()
        }
    }

    applyData(data) {
        let newAttrs = {}
        let changedFields = this.getChangedFieldNames()
        let changedFieldsData = {}
        let willReconnect = false

        changedFields.forEach(function (fieldName) {

            let value = data[fieldName]
            if (value == null) {
                return
            }

            changedFieldsData[fieldName] = value

            /* We're interested only in attributes */
            if (!fieldName.startsWith('attr_')) {
                return
            }

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

            logger.debug(`updating device attribute "${name}" to ${JSON.stringify(value)}`)
            newAttrs[name] = value

            if (this._fullAttrdefs[name].reconnect) {
                willReconnect = true
            }

        }, this)

        if (willReconnect) {
            logger.debug(`device will reconnect`)
        }

        let promise = Promise.resolve()

        if ('name' in newAttrs) {
            let msg = gettext('Are you sure you want to rename the device?')
            promise = new ConfirmMessageForm({message: msg}).show().asPromise()
        }

        if (willReconnect) {
            let msg = gettext('Device will reconnect. Are you sure?')
            promise = new ConfirmMessageForm({message: msg}).show().asPromise()
        }

        if (Object.keys(newAttrs).length) {
            promise = promise.then(function () {

                return DevicesAPI.patchDevice(newAttrs).then(function () {

                    logger.debug(`device attributes successfully updated`)
                    Toast.info(gettext('Device has been updated.'))

                    if ('admin_password' in newAttrs && AuthAPI.getUsername() === 'admin') {
                        logger.debug('admin password also updated locally')
                        AuthAPI.setPassword(newAttrs['admin_password'])
                    }

                    Settings.recentSettingsUpdateTimer.restart()

                }).catch(function (error) {

                    logger.errorStack(`failed to update device attributes`, error)

                    if ((error instanceof BaseAPI.APIError) && (error.code === 'invalid-field')) {
                        let fieldName = `attr_${error.params['field']}`
                        throw new ErrorMapping({[fieldName]: new ValidationError(gettext('Invalid value.'))})
                    }

                    throw error

                })
            })
        }

        /* Apply client settings */
        if (changedFieldsData['theme'] != null) {
            ClientSettings.setTheme(changedFieldsData['theme'])
        }
        if (changedFieldsData['disable_effects'] != null) {
            ClientSettings.setEffectsDisabled(changedFieldsData['disable_effects'])
        }
        if (changedFieldsData['mobile_screen_mode'] != null) {
            ClientSettings.setMobileScreenMode(changedFieldsData['mobile_screen_mode'])
        }
        if (changedFieldsData['scaling_factor'] != null) {
            ClientSettings.setScalingFactor(changedFieldsData['scaling_factor'])
        }

        return promise
    }

    cancelAction() {
        /* Override this to ensure the form is never cancelled/closed */
    }

    navigate(pathId) {
        switch (pathId) {
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
    makeUpdateFirmwareForm() {
        return new UpdateFirmwareForm(Cache.getMainDevice().name)
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeProvisioningForm() {
        return new ProvisioningForm(Cache.getMainDevice().name)
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeConfirmAndRebootForm() {
        let mainDevice = Cache.getMainDevice()
        let displayName = mainDevice.display_name || mainDevice.name

        return this.confirmAndReboot(mainDevice.name, displayName, logger)
    }

}


export default SettingsForm

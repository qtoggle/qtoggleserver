import {gettext}                         from '$qui/base/i18n.js'
import {mix}                             from '$qui/base/mixwith.js'
import {PushButtonField, CompositeField} from '$qui/forms/common-fields.js'
import {PageForm}                        from '$qui/forms/common-forms.js'
import * as Theme                        from '$qui/theme.js'
import * as ObjectUtils                  from '$qui/utils/object.js'

import * as API           from '$app/api.js'
import * as Cache         from '$app/cache.js'
import AttrdefFormMixin   from '$app/common/attrdef-form-mixin.js'
import * as Common        from '$app/common/common.js'
import UpdateFirmwareForm from '$app/common/update-firmware-form.js'
import WaitDeviceMixin    from '$app/common/wait-device-mixin.js'
import RebootDeviceMixin  from '$app/common/reboot-device-mixin.js'

import * as Settings    from './settings.js'


const logger = Settings.logger


/**
 * @class QToggle.SettingsSection.SettingsForm
 * @extends qui.forms.PageForm
 */
export default class SettingsForm extends mix(PageForm).with(AttrdefFormMixin, WaitDeviceMixin, RebootDeviceMixin) {

    constructor() {
        super({
            title: gettext('Settings'),
            icon: Settings.WRENCH_ICON,
            continuousValidation: true
        })

        this._fullAttrdefs = null
        this._staticFieldsAdded = false
    }

    init() {
        this.updateUI()
    }

    /**
     * Updates the entire form (fields & values) from device attributes.
     */
    updateUI() {
        /* Work on copy */
        let attrs = Cache.getMainDevice()
        let attrdefs = ObjectUtils.copy(attrs.definitions, /* deep = */ true)

        this.clearProgress()

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
        this._fullAttrdefs = Common.combineAttrdefs(API.STD_DEVICE_ATTRDEFS, attrdefs)

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

        /* Make sure all defs have a valueToUI function */
        // TODO once AttrDef becomes a class, this will no longer be necessary */
        ObjectUtils.forEach(this._fullAttrdefs, function (name, def) {
            if (!def.valueToUI) {
                def.valueToUI = value => value
            }
        })

        this.fieldsFromAttrdefs(
            this._fullAttrdefs,
            /* extraFieldOptions = */ undefined,
            /* initialData = */ Common.preprocessDeviceAttrs(attrs),
            /* provisioning = */ []
        )

        if (!this._staticFieldsAdded) {
            this.addStaticFields()
            this._staticFieldsAdded = true
        }

        this.updateStaticFields(attrs)
    }

    addStaticFields() {
        this.addField(-1, new CompositeField({
            name: 'management_buttons',
            label: gettext('Manage Device'),
            separator: true,
            fields: [
                new PushButtonField({
                    name: 'reboot',
                    separator: true,
                    caption: gettext('Reboot'),
                    style: 'danger',
                    callback(form) {
                        let mainDevice = Cache.getMainDevice()
                        let displayName = mainDevice.display_name || mainDevice.name
                        form.pushPage(form.confirmAndReboot(mainDevice.name, displayName, logger))
                    }
                }),
                new PushButtonField({
                    name: 'update_firmware',
                    style: 'colored',
                    backgroundColor: Theme.getColor('@magenta-color'),
                    backgroundActiveColor: Theme.getColor('@magenta-active-color'),
                    caption: gettext('Update Firmware'),
                    disabled: true,
                    callback(form) {
                        form.pushPage(form.makeUpdateFirmwareForm())
                    }
                })
            ]
        }))
    }

    updateStaticFields(attrs) {
        let updateFirmwareButtonField = this.getField('management_buttons').getField('update_firmware')
        if (attrs.flags.indexOf('firmware') >= 0) {
            updateFirmwareButtonField.enable()
        }
        else {
            updateFirmwareButtonField.disable()
        }
    }

    applyField(value, fieldName) {
        if (!this._fullAttrdefs) {
            return /* Not loaded */
        }

        let name = fieldName.substring(5)
        if (!(name in this._fullAttrdefs) || !this._fullAttrdefs[name].modifiable) {
            return
        }

        logger.debug(`updating device attribute "${name}" to ${JSON.stringify(value)}`)

        let newAttrs = {[name]: value}

        return API.patchDevice(newAttrs).then(function () {

            logger.debug(`device attribute "${name}" successfully updated`)

            if (name === 'admin_password' && API.getUsername() === 'admin') {
                logger.debug('admin password also updated locally')
                API.setPassword(value)
            }

        }).catch(function (error) {

            logger.errorStack(`failed to update device attribute "${name}"`, error)
            throw error

        })
    }

    defaultAction() {
        /* Prevent the form from closing on enter */
    }

    navigate(pathId) {
        switch (pathId) {
            case 'firmware':
                return this.makeUpdateFirmwareForm()
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeUpdateFirmwareForm() {
        return new UpdateFirmwareForm(Cache.getMainDevice().name)
    }

}

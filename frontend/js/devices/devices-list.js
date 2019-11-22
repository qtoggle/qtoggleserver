import {gettext}           from '$qui/base/i18n.js'
import {CheckField}        from '$qui/forms/common-fields.js'
import {OptionsForm}       from '$qui/forms/common-forms.js'
import {IconLabelListItem} from '$qui/lists/common-items.js'
import {PageList}          from '$qui/lists/common-lists.js'
import * as ArrayUtils     from '$qui/utils/array.js'

import * as Cache from '$app/cache.js'
import * as Utils from '$app/utils.js'

import AddDeviceForm from './add-device-form.js'
import DeviceForm    from './device-form.js'
import * as Devices  from './devices.js'


const DEFAULT_SHOW_OFFLINE_DEVICES = true
const DEFAULT_SHOW_DISABLED_DEVICES = true


/**
 * @class DevicesListOptionsForm
 * @extends qui.forms.OptionsForm
 * @private
 */
class DevicesListOptionsForm extends OptionsForm {

    constructor(deviceList) {
        super({
            page: deviceList,
            fields: [
                new CheckField({
                    name: 'show_offline_devices',
                    label: gettext('Offline Devices')
                }),
                new CheckField({
                    name: 'show_disabled_devices',
                    label: gettext('Disabled Devices')
                })
            ],
            data: {
                show_offline_devices: Cache.getPrefs('devices.show_offline_devices', DEFAULT_SHOW_OFFLINE_DEVICES),
                show_disabled_devices: Cache.getPrefs('devices.show_disabled_devices', DEFAULT_SHOW_DISABLED_DEVICES)
            }
        })
    }

    init() {
        this._updateFieldsVisibility()
    }

    onChange(data, fieldName) {
        Cache.setPrefs(`devices.${fieldName}`, data[fieldName])
        this._updateFieldsVisibility()
    }

    _updateFieldsVisibility() {
        let showDisabledField = this.getField('show_disabled_devices')
        if (this.getUnvalidatedFieldValue('show_offline_devices')) {
            showDisabledField.show()
        }
        else {
            showDisabledField.hide()
        }
    }

}


/**
 * @class DevicesList
 * @extends qui.lists.PageList
 * @private
 */
export default class DevicesList extends PageList {

    constructor() {
        super({
            title: gettext('Devices'),
            icon: Devices.DEVICE_ICON,
            column: true,
            searchEnabled: true,
            addEnabled: true
        })

        this.deviceForm = null
    }

    init() {
        this.updateUI()
    }

    updateUI() {
        let devices = Cache.getSlaveDevices(/* asList = */ true)

        if (!Cache.getPrefs('devices.show_offline_devices', DEFAULT_SHOW_OFFLINE_DEVICES)) {
            devices = devices.filter(d => d.online)
        }

        if (!Cache.getPrefs('devices.show_disabled_devices', DEFAULT_SHOW_DISABLED_DEVICES)) {
            devices = devices.filter(d => d.enabled)
        }

        ArrayUtils.sortKey(devices, device => Utils.alphaNumSortKey(device.attrs.display_name || device.name))

        /* Preserve selected item */
        let selectedItem = this.getSelectedItem()
        let selectedDeviceName = selectedItem && selectedItem.getData()

        this.setItems(devices.map(this.deviceToItem, this))

        if (selectedDeviceName) {
            this.setSelectedIndex(devices.findIndex(function (d) {
                return d.name === selectedDeviceName
            }))
        }
    }

    deviceToItem(device) {
        return new IconLabelListItem({
            label: device.attrs.display_name || device.name,
            icon: Devices.makeDeviceIcon(device),
            data: device.name
        })
    }

    onAdd() {
        return this.pushPage(this.makeAddDeviceForm())
    }

    onSelectionChange(newItem, newIndex, oldItem, oldIndex) {
        return this.pushPage(this.makeDeviceForm(newItem.getData()))
    }

    onCloseNext(next) {
        if (next === this.deviceForm) {
            this.deviceForm = null
            this.setSelectedIndex(-1)
        }
    }

    makeOptionsBarContent() {
        return new DevicesListOptionsForm(this)
    }

    onOptionsChange() {
        this.updateUI()
    }

    navigate(pathId) {
        if (pathId === 'add') {
            return this.makeAddDeviceForm()
        }
        else { /* A device name */
            let device = Cache.getSlaveDevice(pathId)
            if (device) {
                this.setSelectedDevice(pathId)
                return this.makeDeviceForm(pathId)
            }
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeAddDeviceForm() {
        return new AddDeviceForm()
    }

    /**
     * @param {String} deviceName
     * @returns {qui.pages.PageMixin}
     */
    makeDeviceForm(deviceName) {
        return (this.deviceForm = new DeviceForm(deviceName))
    }

    setSelectedDevice(deviceName) {
        this.setSelectedIndex(this.getItems().findIndex(item => item.getData() === deviceName))
    }

}

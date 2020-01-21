
import {gettext}           from '$qui/base/i18n.js'
import {CheckField}        from '$qui/forms/common-fields.js'
import {OptionsForm}       from '$qui/forms/common-forms.js'
import {IconLabelListItem} from '$qui/lists/common-items.js'
import {PageList}          from '$qui/lists/common-lists.js'
import * as ArrayUtils     from '$qui/utils/array.js'

import * as Cache from '$app/cache.js'
import * as Utils from '$app/utils.js'

import * as Ports from './ports.js'
import PortsList  from './ports-list.js'
import {asap}     from '$qui/utils/misc.js'


const DEFAULT_SHOW_OFFLINE_DEVICES = true


/**
 * @class DevicesListOptionsForm
 * @extends qui.forms.OptionsForm
 * @private
 */
class DevicesListOptionsForm extends OptionsForm {

    constructor(devicesList) {
        super({
            page: devicesList,
            fields: [
                new CheckField({
                    name: 'show_offline_devices',
                    label: gettext('Offline Devices')
                })
            ],
            data: {
                show_offline_devices: Cache.getPrefs('ports.show_offline_devices', DEFAULT_SHOW_OFFLINE_DEVICES)
            }
        })
    }

    onChange(data, fieldName) {
        Cache.setPrefs(`ports.${fieldName}`, data[fieldName])
    }

}

/**
 * @class DevicesList
 * @extends qui.lists.PageList
 * @private
 */
class DevicesList extends PageList {

    constructor() {
        super({
            title: gettext('Choose Device'),
            pathId: 'ports',
            icon: Ports.DEVICE_ICON,
            searchEnabled: true,
            column: true
        })

        this.portsList = null
        this._updateUIAsapHandle = null
    }

    init() {
        this.updateUI()
    }

    /**
     * Call updateUI asap, deduplicating calls.
     */
    updateUIAsap() {
        if (this._updateUIAsapHandle != null) {
            clearTimeout(this._updateUIAsapHandle)
        }

        this._updateUIAsapHandle = asap(function () {

            this._updateUIAsapHandle = null
            this.updateUI()

        }.bind(this))
    }

    updateUI() {
        let devices = Cache.getSlaveDevices(/* asList = */ true)

        /* Add special "master" device entry */
        devices.push(Ports.getMasterFakeDevice())

        ArrayUtils.sortKey(devices, function (device) {
            if (Cache.isMainDevice(device.name)) {
                return '' /* Main device is always displayed first */
            }

            return Utils.alphaNumSortKey(device.attrs.display_name || device.name)
        })

        if (!Cache.getPrefs('ports.show_offline_devices', DEFAULT_SHOW_OFFLINE_DEVICES)) {
            devices = devices.filter(d => d.online)
        }

        /* Preserve selected item */
        let selectedItem = this.getSelectedItem()
        let selectedDeviceName = selectedItem && selectedItem.getData()

        this.setItems(devices.map(this.deviceToItem, this))

        if (selectedDeviceName) {
            this.setSelectedIndex(devices.findIndex(d => d.name === selectedDeviceName))
        }
    }

    deviceToItem(device) {
        return new IconLabelListItem({
            label: device.attrs.display_name || device.name,
            icon: Ports.makeDeviceIcon(device),
            data: device.name
        })
    }

    onSelectionChange(newItem, newIndex, oldItem, oldIndex) {
        return this.pushPage(this.makePortsList(newItem.getData()))
    }

    onCloseNext(next) {
        if (next === this.portsList) {
            this.portsList = null
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
        if (Cache.isMainDevice(pathId)) {
            return this.makePortsList(pathId)
        }

        let device = Cache.getSlaveDevice(pathId)
        if (!device) {
            return
        }

        this.setSelectedDevice(pathId)
        return this.makePortsList(pathId)
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makePortsList(deviceName) {
        return (this.portsList = new PortsList(deviceName))
    }

    setSelectedDevice(deviceName) {
        this.setSelectedIndex(this.getItems().findIndex(item => item.getData() === deviceName))
    }

}


export default DevicesList


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
            initialData: {
                show_offline_devices: Cache.getPrefs('ports.show_offline_devices', DEFAULT_SHOW_OFFLINE_DEVICES)
            }
        })
    }

    onChange(data, fieldName) {
        Cache.setPrefs(`ports.${fieldName}`, data[fieldName])
    }

}

/**
 * @alias qtoggle.ports.DevicesList
 * @extends qui.lists.commonlists.PageList
 */
class DevicesList extends PageList {

    /**
     * @constructs
     */
    constructor() {
        super({
            title: gettext('Choose Device'),
            pathId: 'ports',
            icon: Ports.DEVICE_ICON,
            searchEnabled: true,
            columnLayout: true
        })

        this.portsList = null
        this._updateUIASAPHandle = null
    }

    init() {
        this.updateUI()
    }

    /**
     * Call updateUI asap, deduplicating calls.
     */
    updateUIASAP() {
        if (this._updateUIASAPHandle != null) {
            clearTimeout(this._updateUIASAPHandle)
        }

        this._updateUIASAPHandle = asap(function () {

            this._updateUIASAPHandle = null
            this.updateUI()

        }.bind(this))
    }

    /**
     * Update list items from devices.
     */
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
        let oldSelectedItems = this.getSelectedItems()
        let oldSelectedDeviceName = oldSelectedItems.length && oldSelectedItems[0].getData()

        let items = devices.map(this.deviceToItem, this)
        this.setItems(items)

        if (oldSelectedDeviceName) {
            let item = items.find(i => i.getData() === oldSelectedDeviceName)
            if (item) {
                this.setSelectedItems([item])
            }
            else {
                this.setSelectedItems([])
            }
        }
    }

    /**
     * Create list item from device.
     * @param {Object} device
     * @returns {qui.lists.ListItem}
     */
    deviceToItem(device) {
        return new IconLabelListItem({
            label: device.attrs.display_name || device.name,
            icon: Ports.makeDeviceIcon(device),
            data: device.name
        })
    }

    onSelectionChange(oldItems, newItems) {
        if (newItems.length) {
            return this.pushPage(this.makePortsList(newItems[0].getData()))
        }
    }

    onCloseNext(next) {
        if (next === this.portsList) {
            this.portsList = null
            this.setSelectedItems([])
        }
    }

    makeOptionsBarContent() {
        return new DevicesListOptionsForm(this)
    }

    onOptionsChange() {
        this.updateUI()
    }

    navigate(pathId) {
        if (pathId.startsWith('~')) {
            let deviceName = pathId.slice(1)
            if (Cache.isMainDevice(deviceName)) {
                return this.makePortsList(deviceName)
            }

            let device = Cache.getSlaveDevice(deviceName)
            if (!device) {
                return
            }

            this.setSelectedDevice(deviceName)
            return this.makePortsList(deviceName)
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makePortsList(deviceName) {
        return (this.portsList = new PortsList(deviceName))
    }

    /**
     * @param {String} deviceName
     */
    setSelectedDevice(deviceName) {
        let item = this.getItems().find(item => item.getData() === deviceName)
        if (item) {
            this.setSelectedItems([item])
        }
        else {
            this.setSelectedItems([])
        }
    }

}


export default DevicesList

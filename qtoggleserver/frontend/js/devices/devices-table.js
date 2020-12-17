
import {gettext}            from '$qui/base/i18n.js'
import {CheckField}         from '$qui/forms/common-fields/common-fields.js'
import {OptionsForm}        from '$qui/forms/common-forms/common-forms.js'
import {IconLabelTableCell} from '$qui/tables/common-cells/common-cells.js'
import {SimpleTableCell}    from '$qui/tables/common-cells/common-cells.js'
import {PageTable}          from '$qui/tables/common-tables/common-tables.js'
import * as Tables          from '$qui/tables/tables.js'
import * as ArrayUtils      from '$qui/utils/array.js'
import {asap}               from '$qui/utils/misc.js'
import * as Window          from '$qui/window.js'

import * as Cache from '$app/cache.js'
import * as Utils from '$app/utils.js'

import AddDeviceForm          from './add-device-form.js'
import DeviceForm             from './device-form.js'
import * as Devices           from './devices.js'
import DiscoveredDevicesTable from './discovered-devices-table.js'


const DEFAULT_SHOW_OFFLINE_DEVICES = true
const DEFAULT_SHOW_DISABLED_DEVICES = true

const TABLE_HEADER = [gettext('Device'), gettext('IP Address'), gettext('Vendor'), gettext('Firmware')]


class DevicesTableOptionsForm extends OptionsForm {

    constructor(devicesTable) {
        super({
            page: devicesTable,
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
            initialData: {
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
 * @alias qtoggle.devices.DevicesTable
 * @extends qui.tables.commontables.PageTable
 */
class DevicesTable extends PageTable {

    /**
     * @constructs
     */
    constructor() {
        super({
            title: gettext('Devices'),
            icon: Devices.DEVICE_ICON,
            searchEnabled: true,
            addEnabled: true,
            header: TABLE_HEADER,
            rowTemplate: [IconLabelTableCell, SimpleTableCell, SimpleTableCell, SimpleTableCell],
            horizontalAlign: [
                Tables.TABLE_CELL_ALIGN_LEFT,
                Tables.TABLE_CELL_ALIGN_CENTER,
                Tables.TABLE_CELL_ALIGN_CENTER,
                Tables.TABLE_CELL_ALIGN_CENTER
            ]
        })

        this.deviceForm = null
        this._updateUIASAPHandle = null
    }

    init() {
        super.init()

        this.updateUI()
    }

    onBecomeCurrent() {
        this.updateDisplayMode(/* isCurrent = */ true)
    }

    onLeaveCurrent() {
        this.updateDisplayMode(/* isCurrent = */ false)
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
     * Update rows from devices.
     */
    updateUI() {
        let devices = Cache.getSlaveDevices(/* asList = */ true)

        if (!Cache.getPrefs('devices.show_offline_devices', DEFAULT_SHOW_OFFLINE_DEVICES)) {
            devices = devices.filter(d => d.online)
        }

        if (!Cache.getPrefs('devices.show_disabled_devices', DEFAULT_SHOW_DISABLED_DEVICES)) {
            devices = devices.filter(d => d.enabled)
        }

        ArrayUtils.sortKey(devices, device => Utils.alphaNumSortKey(device.attrs.display_name || device.name))

        /* Preserve selected row */
        let selectedDeviceName = this.getSelectedDeviceName()

        this.setRows([])
        let rowValuesList = devices.map(this.deviceToRowValues, this)
        rowValuesList.map(rowValues => this.addRowValues(-1, rowValues.slice(1), rowValues[0]))

        if (selectedDeviceName) {
            this.setSelectedDeviceName(selectedDeviceName)
        }
    }

    updateDisplayMode(isCurrent) {
        let listMode = !isCurrent || Window.isSmallScreen() /* Always use list mode on small screens */
        if (listMode) {
            this.setVisibilities([true, false, false, false])
            this.setHeader(null)
            this.setColumnLayout(true)
        }
        else {
            this.setVisibilities(null)
            this.setHeader(TABLE_HEADER)
            this.setColumnLayout(false)
        }
    }

    /**
     * Create table row from device.
     * @param {Object} device
     * @returns {Array}
     */
    deviceToRowValues(device) {
        return [
            device, /* First element is the row data */
            {
                label: device.attrs.display_name || device.name,
                icon: Devices.makeDeviceIcon(device)
            },
            device.attrs['ip_address_current'],
            device.attrs['vendor'],
            device.attrs['version']
        ]
    }

    onAdd() {
        return this.pushPage(this.makeAddDeviceForm())
    }

    onSelectionChange(oldRows, newRows) {
        if (newRows.length) {
            return this.pushPage(this.makeDeviceForm(newRows[0].getData().name))
        }
    }

    onCloseNext(next) {
        if (next === this.deviceForm) {
            this.deviceForm = null
            this.setSelectedDeviceName(null)
        }
    }

    makeOptionsBarContent() {
        return new DevicesTableOptionsForm(this)
    }

    onOptionsChange(options) {
        this.updateUI()
    }

    navigate(pathId) {
        if (pathId === 'add') {
            return this.makeAddDeviceForm()
        }
        else if (pathId === 'discover') {
            return this.makeDiscoverDevicesTable()
        }
        else if (pathId.startsWith('~')) { /* A device name */
            let deviceName = pathId.slice(1)
            let device = Cache.getSlaveDevice(deviceName)
            if (device) {
                /* We need to delay here using asap() to overcome missing port item due to usage of updateUIASAP */
                asap(() => this.setSelectedDeviceName(deviceName))
                return this.makeDeviceForm(deviceName)
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
     * @returns {qui.pages.PageMixin}
     */
    makeDiscoverDevicesTable() {
        return new DiscoveredDevicesTable()
    }

    /**
     * @param {String} deviceName
     * @returns {qui.pages.PageMixin}
     */
    makeDeviceForm(deviceName) {
        return (this.deviceForm = new DeviceForm(deviceName))
    }

    /**
     * @param {?String} deviceName
     */
    setSelectedDeviceName(deviceName) {
        this.setSelectedRows(this.getRows().filter(r => r.getData().name === deviceName))
    }

    /**
     * @returns {?String}
     */
    getSelectedDeviceName() {
        let selectedRows = this.getSelectedRows()
        if (selectedRows.length) {
            return selectedRows[0].getData().name
        }
        else {
            return null
        }
    }

}


export default DevicesTable

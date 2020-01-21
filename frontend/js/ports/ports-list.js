
import {AssertionError}    from '$qui/base/errors.js'
import {gettext}           from '$qui/base/i18n.js'
import Config              from '$qui/config.js'
import {CheckField}        from '$qui/forms/common-fields.js'
import {OptionsForm}       from '$qui/forms/common-forms.js'
import {IconLabelListItem} from '$qui/lists/common-items.js'
import {PageList}          from '$qui/lists/common-lists.js'
import * as ArrayUtils     from '$qui/utils/array.js'
import {asap}              from '$qui/utils/misc.js'

import * as Cache from '$app/cache.js'
import * as Utils from '$app/utils.js'

import AddPortForm from './add-port-form.js'
import PortForm    from './port-form.js'
import * as Ports  from './ports.js'


const DEFAULT_SHOW_OFFLINE_PORTS = true
const DEFAULT_SHOW_DISABLED_PORTS = true


/**
 * @class PortsListOptionsForm
 * @extends qui.forms.OptionsForm
 * @private
 */
class PortsListOptionsForm extends OptionsForm {

    constructor(portsList) {
        super({
            page: portsList,
            fields: [
                new CheckField({
                    name: 'show_offline_ports',
                    label: gettext('Offline Ports')
                }),
                new CheckField({
                    name: 'show_disabled_ports',
                    label: gettext('Disabled Ports')
                })
            ],
            data: {
                show_offline_ports: Cache.getPrefs('ports.show_offline_ports', DEFAULT_SHOW_OFFLINE_PORTS),
                show_disabled_ports: Cache.getPrefs('ports.show_disabled_ports', DEFAULT_SHOW_DISABLED_PORTS)
            }
        })
    }

    init() {
        this._updateFieldsVisibility()
    }

    onChange(data, fieldName) {
        Cache.setPrefs(`ports.${fieldName}`, data[fieldName])
        this._updateFieldsVisibility()
    }

    _updateFieldsVisibility() {
        let showDisabledField = this.getField('show_disabled_ports')
        if (this.getUnvalidatedFieldValue('show_offline_ports')) {
            showDisabledField.show()
        }
        else {
            showDisabledField.hide()
        }
    }

}


/**
 * @class PortsList
 * @extends qui.lists.PageList
 * @private
 * @param {String} [deviceName]
 */
class PortsList extends PageList {

    constructor(deviceName = null) {
        super({
            column: true,
            pathId: deviceName || Cache.getMainDevice().name,
            title: gettext('Ports'),
            icon: Ports.PORT_ICON,
            searchEnabled: true
        })

        let title
        if (deviceName) {
            if (Cache.isMainDevice(deviceName)) {
                let mainDevice = Cache.getMainDevice()
                title = mainDevice.display_name || mainDevice.name
            }
            else { /* A slave device */
                let device = Cache.getSlaveDevice(deviceName)
                if (!device) {
                    throw new AssertionError(`Device with name ${deviceName} not found in cache`)
                }

                title = device.attrs.display_name || device.name
            }
        }
        else { /* Slaves not enabled */
            title = gettext('Ports')
        }

        this._deviceName = deviceName
        this._updateUIAsapHandle = null
        this.portForm = null

        this.setTitle(title)
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
        let ports = Cache.getPorts(/* asList = */ true)

        if (this._deviceName && !Cache.isMainDevice(this._deviceName)) { /* A slave device */
            ports = ports.filter(function (p) {
                let d = Cache.findPortSlaveDevice(p.id)
                return d && d.name === this._deviceName
            }, this)

            /* Adding virtual ports is enabled only if device is online and there still are virtual ports available */
            let devices = Cache.getSlaveDevices()
            let device = devices[this._deviceName]

            let virtualPorts = ports.filter(p => p.virtual)
            if (device && device.online && (device.attrs.virtual_ports || 0) > virtualPorts.length) {
                this.enableAdd()
            }
            else {
                this.disableAdd()
            }
        }
        else { /* Master device or slaves not enabled */
            if (Config.slavesEnabled) {
                /* Filter out slave ports */
                ports = ports.filter(p => Cache.findPortSlaveDevice(p.id) == null)
            }

            if ((Cache.getMainDevice().virtual_ports || 0) > ports.length) {
                this.enableAdd()
            }
            else {
                this.disableAdd()
            }
        }

        if (!Cache.getPrefs('ports.show_offline_ports', DEFAULT_SHOW_OFFLINE_PORTS)) {
            ports = ports.filter(p => p.online !== false) /* null or undefined also mean online */
        }

        if (!Cache.getPrefs('ports.show_disabled_ports', DEFAULT_SHOW_DISABLED_PORTS)) {
            ports = ports.filter(p => p.enabled)
        }

        ArrayUtils.sortKey(ports, port => Utils.alphaNumSortKey(port.display_name || port.id))

        /* Preserve selected item */
        let selectedItem = this.getSelectedItem()
        let selectedPortId = selectedItem && selectedItem.getData()

        this.setItems(ports.map(this.portToItem, this))

        if (selectedPortId) {
            this.setSelectedIndex(ports.findIndex(function (p) {
                return p.id === selectedPortId
            }))
        }
    }

    portToItem(port) {
        let label = port.display_name
        if (!label) {
            label = port.id
            if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                label = label.substring(this._deviceName.length + 1)
            }
        }

        return new IconLabelListItem({
            label: label,
            icon: Ports.makePortIcon(port),
            data: port.id
        })
    }

    getDeviceName() {
        return this._deviceName
    }

    onAdd() {
        return this.pushPage(this.makeAddPortForm(this._deviceName))
    }

    onSelectionChange(newItem, newIndex, oldItem, oldIndex) {
        return this.pushPage(this.makePortForm(newItem.getData()))
    }

    onCloseNext(next) {
        if (next === this.portForm) {
            this.portForm = null
            this.setSelectedIndex(-1)
        }
    }

    onOptionsChange() {
        this.updateUI()
    }

    makeOptionsBarContent() {
        return new PortsListOptionsForm(this)
    }

    navigate(pathId) {
        if (pathId === 'add') {
            return this.makeAddPortForm(this._deviceName)
        }
        else { /* A port id */
            let portId
            if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                portId = `${this._deviceName}.${pathId}`
            }
            else {
                portId = pathId
            }

            let port = Cache.getPort(portId)
            if (port) {
                this.setSelectedPort(portId)
                return this.makePortForm(portId)
            }
        }
    }

    /**
     * @param {String} [deviceName]
     * @returns {qui.pages.PageMixin}
     */
    makeAddPortForm(deviceName) {
        return new AddPortForm(deviceName)
    }

    /**
     * @param {String} portId
     * @returns {qui.pages.PageMixin}
     */
    makePortForm(portId) {
        return (this.portForm = new PortForm(portId, this._deviceName))
    }

    setSelectedPort(portId) {
        this.setSelectedIndex(this.getItems().findIndex(item => item.getData() === portId))
    }

}


export default PortsList

import * as Cache           from '$app/cache.js'
import * as Constants       from '$app/constants.js'
import * as Utils           from '$app/utils.js'
import {AssertionError}     from '$qui/base/errors.js'
import {gettext}            from '$qui/base/i18n.js'
import Config               from '$qui/config.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields/common-fields.js'
import {OptionsForm}        from '$qui/forms/common-forms/common-forms.js'
import {IconLabelListItem}  from '$qui/lists/common-items/common-items.js'
import {PageList}           from '$qui/lists/common-lists/common-lists.js'
import * as Theme           from '$qui/theme.js'
import * as ArrayUtils      from '$qui/utils/array.js'
import Debouncer            from '$qui/utils/debouncer.js'
import {asap}               from '$qui/utils/misc.js'
import * as ObjectUtils     from '$qui/utils/object.js'

import AddPortForm from './add-port-form.js'
import PortForm    from './port-form.js'
import * as Ports  from './ports.js'


const DEFAULT_FILTER = 'all'

/* One choice buttons field per filter. The choice named by `DEFAULT_FILTER` matches everything and so has no `test`.
 *
 * Only virtual ports report `virtual`, so `!port.virtual` is what "real" means. Only an enabled port has a meaningful
 * online state: a disabled peripheral or slave port reports `online: false` while a disabled virtual port omits
 * `online` entirely, so both online choices require `enabled` and a disabled port shows up under "All" alone. That
 * matches the icon, which decorates a disabled port neither green nor grey. */
const PORT_FILTERS = [
    {
        name: 'online',
        label: gettext('Online Status'),
        choices: [
            {value: 'offline', label: gettext('Offline'), test: port => port.enabled && port.online === false},
            {value: 'online', label: gettext('Online'), test: port => port.enabled && port.online !== false},
            {value: DEFAULT_FILTER, label: gettext('All')}
        ]
    },
    {
        name: 'enabled',
        label: gettext('Enabled Status'),
        choices: [
            {value: 'disabled', label: gettext('Disabled'), test: port => !port.enabled},
            {value: 'enabled', label: gettext('Enabled'), test: port => port.enabled},
            {value: DEFAULT_FILTER, label: gettext('All')}
        ]
    },
    {
        name: 'type',
        label: gettext('Type'),
        choices: [
            {value: 'boolean', label: gettext('Boolean'), test: port => port.type === 'boolean'},
            {value: 'number', label: gettext('Number'), test: port => port.type === 'number'},
            {value: DEFAULT_FILTER, label: gettext('All')}
        ]
    },
    {
        name: 'writable',
        label: gettext('Writable'),
        choices: [
            {value: 'read-only', label: gettext('Read-only'), test: port => !port.writable},
            {value: 'writable', label: gettext('Writable'), test: port => port.writable},
            {value: DEFAULT_FILTER, label: gettext('All')}
        ]
    },
    {
        name: 'virtual',
        label: gettext('Virtual'),
        choices: [
            {value: 'virtual', label: gettext('Virtual'), test: port => port.virtual},
            {value: 'real', label: gettext('Real'), test: port => !port.virtual},
            {value: DEFAULT_FILTER, label: gettext('All')}
        ]
    }
]


function getPortFilterValue(filter) {
    return Cache.getPrefs(`ports.filter_${filter.name}`, DEFAULT_FILTER)
}

function filterPorts(ports) {
    return PORT_FILTERS.reduce(function (ports, filter) {
        let value = getPortFilterValue(filter)
        let choice = filter.choices.find(choice => choice.value === value)

        return choice && choice.test ? ports.filter(choice.test) : ports
    }, ports)
}


class PortsListOptionsForm extends OptionsForm {

    constructor(portsList) {
        super({
            page: portsList,
            fields: PORT_FILTERS.map(filter => new ChoiceButtonsField({
                name: filter.name,
                label: filter.label,
                choices: filter.choices.map(({value, label}) => ({value: value, label: label}))
            })),
            initialData: ObjectUtils.fromEntries(
                PORT_FILTERS.map(filter => [filter.name, getPortFilterValue(filter)])
            )
        })
    }

    onChange(data, fieldName) {
        Cache.setPrefs(`ports.filter_${fieldName}`, data[fieldName])
    }

}


/**
 * alias qtoggle.ports.PortIconLabelListItem
 * @extends qui.lists.commonitems.IconLabelListItem
 */
class PortIconLabelListItem extends IconLabelListItem {

    constructor({flags = [], ...args} = {}) {
        super(args)

        this._flags = flags
        this._flagsElement = null
    }

    makeIconLabelContainer() {
        let container = super.makeIconLabelContainer()

        /* Raw DOM rather than jQuery: this runs 448 times on the hub's port list, where jQuery's element, style and
         * append helpers came to about 470 ms of the 4.6 s the list takes to build. */
        this._flagsElement = document.createElement('div')
        this._flagsElement.className = 'port-flags'
        this._flags.forEach(({text, color, active}) => {
            let flagElement = document.createElement('div')
            flagElement.className = 'flag'
            flagElement.textContent = text
            flagElement.style.background = color
            flagElement.style.visibility = active ? 'visible' : 'hidden'
            this._flagsElement.appendChild(flagElement)
        })
        container[0].appendChild(this._flagsElement)

        return container
    }

    updateFrom(other) {
        if (!super.updateFrom(other)) {
            return false
        }

        /* The parent class knows nothing about the flags, so without this a row kept in place goes on showing the
         * badges it was built with. Only `active` ever differs in practice; a different set of flags means a
         * different row, which the list rebuilds instead. */
        let sameFlags = other._flags.length === this._flags.length && other._flags.every(
            (f, i) => f.text === this._flags[i].text && f.color === this._flags[i].color
        )
        if (!sameFlags) {
            return false
        }

        let flagElements = this._flagsElement ? this._flagsElement.children : null
        other._flags.forEach(function ({active}, i) {
            if (flagElements && active !== this._flags[i].active) {
                flagElements[i].style.visibility = active ? 'visible' : 'hidden'
            }
        }, this)
        this._flags = other._flags

        return true
    }

}


/**
 * @alias qtoggle.ports.PortsList
 * @extends qui.lists.commonlists.PageList
 */
class PortsList extends PageList {

    /**
     * @constructs
     * @param {?String} [deviceName]
     */
    constructor(deviceName = null) {
        super({
            columnLayout: true,
            pathId: `~${deviceName || Cache.getMainDevice().name}`,
            title: gettext('Ports'),
            icon: Ports.PORT_ICON,
            searchEnabled: true,
            cssClass: 'ports-list'
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
        this._updateUIDebouncer = new Debouncer(
            () => this.updateUI(), Constants.COMMON_DEBOUNCE_DELAY, Constants.COMMON_DEBOUNCE_MAX_WAIT
        )
        this.portForm = null

        this.setTitle(title)
    }

    init() {
        this.updateUI()
    }

    /**
     * Call updateUI asap, deduplicating calls.
     */
    updateUIASAP() {
        this._updateUIDebouncer.call()
    }

    /**
     * Update list items from ports.
     */
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

        ports = filterPorts(ports)

        ArrayUtils.sortKey(ports, port => Utils.alphaNumSortKey(port.display_name || port.id))

        /* Preserve selected item */
        let oldSelectedItems = this.getSelectedItems()
        let oldSelectedPortId = oldSelectedItems.length && oldSelectedItems[0].getData()

        let items = ports.map(this.portToItem, this)
        this.setItems(items)

        if (oldSelectedPortId) {
            let item = items.find(i => i.getData() === oldSelectedPortId)
            if (item) {
                this.setSelectedItems([item])
            }
            else {
                this.setSelectedItems([])
            }
        }
    }

    /**
     * Create list item from port.
     * @param {Object} port
     * @returns {qui.lists.ListItem}
     */
    portToItem(port) {
        let label = port.display_name
        let subLabel = null
        if (label) {
            subLabel = port.id
            if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                subLabel = subLabel.substring(this._deviceName.length + 1)
            }
        }
        else {
            label = port.id
            if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                label = label.substring(this._deviceName.length + 1)
            }
        }

        return new PortIconLabelListItem({
            label: label,
            subLabel: subLabel,
            icon: Ports.makePortIcon(port),
            flags: this._makePortFlags(port),
            data: port.id
        })
    }

    _makePortFlags(port) {
        return [
            {text: 'W', color: Theme.getVar('orange-color'), active: port.writable},
            {text: 'V', color: Theme.getVar('magenta-color'), active: port.virtual}
        ]
    }

    /**
     * @returns {?String}
     */
    getDeviceName() {
        return this._deviceName
    }

    onAdd() {
        return this.pushPage(this.makeAddPortForm(this._deviceName))
    }

    onSelectionChange(oldItems, newItems) {
        if (newItems.length) {
            return this.pushPage(this.makePortForm(newItems[0].getData()))
        }
    }

    onCloseNext(next) {
        if (next === this.portForm) {
            this.portForm = null
            this.setSelectedItems([])
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
        else if (pathId.startsWith('~')) { /* A port id */
            let portId
            if (this._deviceName && !Cache.isMainDevice(this._deviceName)) {
                portId = `${this._deviceName}.${pathId.slice(1)}`
            }
            else {
                portId = pathId.slice(1)
            }

            let port = Cache.getPort(portId)
            if (port) {
                /* We need to delay here using asap() to overcome missing port item due to usage of updateUIASAP */
                asap(() => this.setSelectedPort(portId))
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

    /**
     * @param {String} portId
     */
    setSelectedPort(portId) {
        let item = this.getItems().find(item => item.getData() === portId)
        if (item) {
            this.setSelectedItems([item])
        }
        else {
            this.setSelectedItems([])
        }
    }

}


export default PortsList

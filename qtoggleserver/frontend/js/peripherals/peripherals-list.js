
import {gettext}           from '$qui/base/i18n.js'
import {IconLabelListItem} from '$qui/lists/common-items/common-items.js'
import {PageList}          from '$qui/lists/common-lists/common-lists.js'
import * as ArrayUtils     from '$qui/utils/array.js'

import * as PeripheralsAPI from '$app/api/peripherals.js'
import * as Utils          from '$app/utils.js'

import AddPeripheralForm from './add-peripheral-form.js'
import PeripheralForm    from './peripheral-form.js'
import * as Peripherals  from './peripherals.js'


/**
 * @alias qtoggle.peripherals.PeripheralsList
 * @extends qui.lists.commonlists.PageList
 */
class PeripheralsList extends PageList {

    /**
     * @constructs
     */
    constructor() {
        super({
            columnLayout: true,
            title: gettext('Peripherals'),
            icon: Peripherals.PERIPHERAL_ICON,
            searchEnabled: true,
            addEnabled: true
        })

        this.peripheralForm = null
    }

    load() {
        return this.updateUI()
    }

    /**
     * Update list items from peripherals.
     * @returns {Promise}
     */
    updateUI() {
        return PeripheralsAPI.getPeripherals().then(function (peripherals) {
            ArrayUtils.sortKey(peripherals, p => Utils.alphaNumSortKey(p.id))

            /* Preserve selected item */
            let oldSelectedItems = this.getSelectedItems()
            let oldSelectedId = oldSelectedItems.length && oldSelectedItems[0].getData()

            let items = peripherals.map(this.peripheralToItem, this)
            this.setItems(items)

            if (oldSelectedId) {
                let item = items.find(i => i.getData() === oldSelectedId)
                if (item) {
                    this.setSelectedItems([item])
                }
                else {
                    this.setSelectedItems([])
                }
            }
        }.bind(this))
    }

    /**
     * Create list item from peripheral.
     * @param {Object} peripheral
     * @returns {qui.lists.ListItem}
     */
    peripheralToItem(peripheral) {
        return new IconLabelListItem({
            label: peripheral.id,
            subLabel: peripheral.driver.split('.').slice(-1)[0],
            icon: Peripherals.PERIPHERAL_ICON,
            data: peripheral.id
        })
    }

    onAdd() {
        return this.pushPage(this.makeAddPeripheralForm())
    }

    onSelectionChange(oldItems, newItems) {
        if (newItems.length) {
            return this.pushPage(this.makePeripheralForm(newItems[0].getData()))
        }
    }

    onCloseNext(next) {
        if (next === this.peripheralForm) {
            this.peripheralForm = null
            this.setSelectedItems([])
        }
    }

    navigate(pathId) {
        if (pathId === 'add') {
            return this.makeAddPeripheralForm()
        }
        else if (pathId.startsWith('~')) { /* A peripheral id */
            let peripheralId = pathId.slice(1)
            return PeripheralsAPI.getPeripherals().then(function (peripherals) {
                let peripheral = peripherals.find(p => p.id === peripheralId)
                if (peripheral) {
                    this.setSelectedPeripheral(peripheralId)
                    return this.makePeripheralForm(peripheralId)
                }
            }.bind(this))
        }
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeAddPeripheralForm() {
        return new AddPeripheralForm()
    }

    /**
     * @param {String} peripheralId
     * @returns {qui.pages.PageMixin}
     */
    makePeripheralForm(peripheralId) {
        return (this.peripheralForm = new PeripheralForm(peripheralId))
    }

    /**
     * @param {String} peripheralId
     */
    setSelectedPeripheral(peripheralId) {
        let item = this.getItems().find(item => item.getData() === peripheralId)
        if (item) {
            this.setSelectedItems([item])
        }
        else {
            this.setSelectedItems([])
        }
    }

}


export default PeripheralsList

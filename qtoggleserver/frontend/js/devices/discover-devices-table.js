
import {gettext}             from '$qui/base/i18n.js'
import StockIcon             from '$qui/icons/stock-icon.js'
import {ANIMATION_SPIN}      from '$qui/icons/icons.js'
import {PushButtonTableCell} from '$qui/tables/common-cells.js'
import {SimpleTableCell}     from '$qui/tables/common-cells.js'
import {PageTable}           from '$qui/tables/common-tables.js'
// import * as Window           from '$qui/window.js'

import * as Devices from './devices.js'


// const logger = Devices.logger


class AdoptTableCell extends PushButtonTableCell {

    constructor() {
        super({
            caption: gettext('Adopt')
        })
    }

    onClick() {
        this.setIcon(new StockIcon({name: 'sync', animation: ANIMATION_SPIN}))
        this.setEnabled(false)
        this.setCaption(gettext('Adopting...'))
    }

}


/**
 * @alias qtoggle.devices.DiscoverDevicesTable
 * @extends qui.tables.commontables.PageTable
 */
class DiscoverDevicesTable extends PageTable {

    /**
     * @constructs
     */
    constructor() {
        super({
            icon: Devices.DEVICE_ICON,
            title: gettext('Discovered Devices'),
            pathId: 'discover',
            selectMode: 'disabled',
            // widths: ['1fr', '1fr', '1fr'],
            searchEnabled: true,
            header: ['Name', 'IP Address', 'Actions'],
            rowTemplate: [SimpleTableCell, SimpleTableCell, AdoptTableCell]
        })
    }

    load() {
        this.addRowValues(-1, ['First Device', '192.168.1.3'])
        this.addRowValues(-1, ['Second Device', '192.168.1.4'])

        return Promise.resolve()
    }

}


export default DiscoverDevicesTable


import {gettext} from '$qui/base/i18n.js'

import * as AuthAPI from '$app/api/auth.js'
import {Section}    from '$app/sections.js'

import * as Peripherals from './peripherals.js'
import PeripheralsList  from './peripherals-list.js'


const SECTION_ID = 'peripherals'
const SECTION_TITLE = gettext('Peripherals')


/**
 * @alias qtoggle.peripherals.PeripheralsSection
 * @extends qtoggle.sections.Section
 */
class PeripheralsSection extends Section {

    /**
     * @constructs
     */
    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Peripherals.PERIPHERAL_ICON
        })

        this.peripheralsList = null
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makePeripheralsList() {
        return (this.peripheralsList = new PeripheralsList())
    }

    updatePeripheralsList() {
        this.peripheralsList.updateUI()
    }

    makeMainPage() {
        if (AuthAPI.getCurrentAccessLevel() < AuthAPI.ACCESS_LEVEL_ADMIN) {
            return this.makeForbiddenMessage()
        }

        return this.makePeripheralsList()
    }

}


export default PeripheralsSection

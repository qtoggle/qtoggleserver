
import {gettext} from '$qui/base/i18n.js'
import * as Toast from '$qui/messages/toast.js'
import * as StringUtils from '$qui/utils/string.js'

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

    onServerEvent(event) {
        if (!this.peripheralsList) {
            return
        }

        let peripheralForm = this.peripheralsList.peripheralForm
        let peripheralId = event.params && event.params.id

        switch (event.type) {
            case 'peripheral-update':
            case 'peripheral-remove': {
                this.peripheralsList.updateUIASAP()

                if (event.type === 'peripheral-update') {
                    if (peripheralId) {
                        Toast.info(StringUtils.formatPercent(gettext('Peripheral %(id)s has been updated.'), {
                            id: peripheralId
                        }))
                    }
                    else {
                        Toast.info(gettext('Peripheral has been updated.'))
                    }

                    if (peripheralForm && (peripheralForm.getPeripheralId() === peripheralId)) {
                        peripheralForm.setIcon(Peripherals.makePeripheralIcon(event.params))
                    }
                }
                else {
                    if (peripheralId) {
                        Toast.info(StringUtils.formatPercent(gettext('Peripheral %(id)s has been removed.'), {
                            id: peripheralId
                        }))
                    }
                    else {
                        Toast.info(gettext('Peripheral has been removed.'))
                    }

                    if (peripheralForm && (peripheralForm.getPeripheralId() === peripheralId)) {
                        peripheralForm.close(/* force = */ true)
                    }
                }

                break
            }

            case 'peripheral-add': {
                this.peripheralsList.updateUIASAP()
                if (peripheralId) {
                    Toast.info(StringUtils.formatPercent(gettext('Peripheral %(id)s has been added.'), {
                        id: peripheralId
                    }))
                }
                else {
                    Toast.info(gettext('Peripheral has been added.'))
                }
                break
            }
        }
    }

    makeMainPage() {
        if (AuthAPI.getCurrentAccessLevel() < AuthAPI.ACCESS_LEVEL_ADMIN) {
            return this.makeForbiddenMessage()
        }

        return this.makePeripheralsList()
    }

}


export default PeripheralsSection

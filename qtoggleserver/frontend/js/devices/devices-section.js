
import {gettext}        from '$qui/base/i18n.js'
import {getCurrentPage} from '$qui/pages/pages.js'

import * as AuthAPI    from '$app/api/auth.js'
import * as Cache      from '$app/cache.js'
import WaitDeviceMixin from '$app/common/wait-device-mixin.js'
import {Section}       from '$app/sections.js'

import * as Devices from './devices.js'
import DevicesTable from './devices-table.js'


const SECTION_ID = 'devices'
const SECTION_TITLE = gettext('Devices')


/**
 * @alias qtoggle.devices.DevicesSection
 * @extends qtoggle.sections.Section
 */
class DevicesSection extends Section {

    /**
     * @constructs
     */
    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Devices.DEVICE_ICON
        })

        this.devicesTable = null
    }

    load() {
        let promises = [
            Cache.whenDeviceCacheReady,
            Cache.whenPrefsCacheReady,
            Cache.whenSlaveDevicesCacheReady
        ]

        return Promise.all(promises)
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeDevicesTable() {
        return (this.devicesTable = new DevicesTable())
    }

    onServerEvent(event) {
        /* Don't handle any event unless the devices table has been created */
        if (!this.devicesTable) {
            return
        }

        let deviceForm = this.devicesTable.deviceForm

        switch (event.type) {
            case 'slave-device-update': {
                this.devicesTable.updateUIASAP()

                if (deviceForm && (deviceForm.getDeviceName() === event.params.name)) {
                    let fieldChangeWarnings = !event.expected && !Devices.recentDeviceUpdateTimer.isRunning()
                    deviceForm.updateUI(fieldChangeWarnings)
                }

                let currentPage = getCurrentPage()
                if ((Devices.getCurrentDeviceName() === event.params.name) && currentPage &&
                    (currentPage instanceof WaitDeviceMixin)) {

                    if (!event.params.online && currentPage.isWaitingDeviceOffline()) {
                        currentPage.fulfillDeviceOffline()
                    }
                    else if (event.params.online && currentPage.isWaitingDeviceOnline()) {
                        currentPage.fulfillDeviceOnline()
                    }
                }

                break
            }

            case 'slave-device-polling-update': {
                if (deviceForm && (deviceForm.getDeviceName() === event.params.name)) {
                    deviceForm.updateUI(/* fieldChangeWarnings = */ false)
                }

                break
            }

            case 'slave-device-add': {
                this.devicesTable.updateUIASAP()

                /* Handle special case where currently selected device has been locally renamed via the device form */
                if (Devices.getRenamedDeviceName() === event.params.name) {
                    let device = Cache.getSlaveDevice(event.params.name)
                    if (device) {
                        deviceForm = this.devicesTable.makeDeviceForm(device.name)
                        this.devicesTable.updateUI()
                        this.devicesTable.setSelectedDeviceName(device.name)
                        this.devicesTable.pushPage(deviceForm)
                        deviceForm.startWaitingDeviceOnline()
                    }
                }

                break
            }

            case 'slave-device-remove': {
                this.devicesTable.updateUIASAP()

                if (deviceForm && (deviceForm.getDeviceName() === event.params.name) &&
                    (Devices.getRenamedDeviceName() == null)) {

                    /* The device that is currently selected has just been removed */
                    deviceForm.close(/* force = */ true)
                }

                break
            }
        }
    }

    makeMainPage() {
        if (AuthAPI.getCurrentAccessLevel() < AuthAPI.ACCESS_LEVEL_ADMIN) {
            return this.makeForbiddenMessage()
        }

        return this.makeDevicesTable()
    }

}


export default DevicesSection

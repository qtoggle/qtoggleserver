
import {gettext} from '$qui/base/i18n.js'

import * as API   from '$app/api.js'
import * as Cache from '$app/cache.js'
import {Section}  from '$app/sections.js'

import * as Devices from './devices.js'
import DevicesList  from './devices-list.js'


const SECTION_ID = 'devices'
const SECTION_TITLE = gettext('Devices')


export default class DevicesSection extends Section {

    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Devices.DEVICE_ICON
        })

        this.devicesList = null
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
    makeDevicesList() {
        return (this.devicesList = new DevicesList())
    }

    onServerEvent(event) {
        /* Don't handle any event unless the main list has been created */
        if (!this.devicesList) {
            return
        }

        let deviceForm = this.devicesList.deviceForm

        switch (event.type) {
            case 'slave-device-update': {
                this.devicesList.updateUI()

                if (deviceForm && deviceForm.getDeviceName() === event.params.name) {
                    if (!event.params.online && deviceForm.isWaitingDeviceOffline()) {
                        deviceForm.fulfillDeviceOffline()
                    }
                    else if (event.params.online && deviceForm.isWaitingDeviceOnline()) {
                        deviceForm.fulfillDeviceOnline()
                    }

                    deviceForm.updateUI()
                }

                break
            }

            case 'slave-device-add': {
                this.devicesList.updateUI()

                /* Handle special case where currently selected device has been locally renamed via the device form */
                if (deviceForm && deviceForm.getRenamedDeviceNewName() === event.params.name) {
                    let device = Cache.getSlaveDevice(event.params.name)
                    if (device) {
                        deviceForm = this.devicesList.makeDeviceForm(device.name)
                        this.devicesList.setSelectedDevice(device.name)
                        this.devicesList.pushPage(deviceForm)
                        deviceForm.setWaitingDeviceOnline()
                    }
                }

                break
            }

            case 'slave-device-remove': {
                this.devicesList.updateUI()

                if (deviceForm && deviceForm.getDeviceName() === event.params.name &&
                    deviceForm.getRenamedDeviceNewName() == null) {

                    /* The device that is currently selected has just been removed */
                    deviceForm.close()
                }

                break
            }
        }
    }

    makeMainPage() {
        if (API.getCurrentAccessLevel() < API.ACCESS_LEVEL_ADMIN) {
            return
        }

        return this.makeDevicesList()
    }

}

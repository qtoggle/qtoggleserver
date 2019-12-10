
import {gettext} from '$qui/base/i18n.js'
import Config    from '$qui/config.js'

import * as API   from '$app/api.js'
import * as Cache from '$app/cache.js'
import {Section}  from '$app/sections.js'

import DevicesList from './devices-list.js'
import * as Ports  from './ports.js'
import PortsList   from './ports-list.js'


const SECTION_ID = 'ports'
const SECTION_TITLE = gettext('Ports')


export default class PortsSection extends Section {

    constructor() {
        super({
            id: SECTION_ID,
            title: SECTION_TITLE,
            icon: Ports.PORT_ICON
        })

        this.devicesList = null
        this.portsList = null
    }

    load() {
        let promises = [
            Cache.whenDeviceCacheReady,
            Cache.whenPortsCacheReady,
            Cache.whenPrefsCacheReady
        ]

        if (Config.slavesEnabled) {
            promises.push(Cache.whenSlaveDevicesCacheReady)
        }

        return Promise.all(promises)
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makePortsList() {
        return (this.portsList = new PortsList())
    }

    /**
     * @returns {qui.pages.PageMixin}
     */
    makeDevicesList() {
        return (this.devicesList = new DevicesList())
    }

    onServerEvent(event) {
        let portsList = null

        if (this.devicesList) {
            portsList = this.devicesList.portsList
        }
        else {
            portsList = this.portsList
        }

        let portForm = portsList ? portsList.portForm : null

        switch (event.type) {
            case 'device-update': {
                if (!this.devicesList) {
                    break
                }

                Ports.clearMasterFakeDevice()
                this.devicesList.updateUIAsap()

                break
            }

            case 'slave-device-update': {
                if (!this.devicesList) {
                    break
                }

                this.devicesList.updateUIAsap()
                if (portsList && portsList.getDeviceName() === event.params.name) {
                    portsList.updateUIAsap()
                }

                break
            }

            case 'slave-device-add': {
                if (!this.devicesList) {
                    break
                }

                this.devicesList.updateUIAsap()

                break
            }

            case 'slave-device-remove': {
                if (!this.devicesList) {
                    break
                }

                this.devicesList.updateUIAsap()

                if (portsList && portsList.getDeviceName() === event.params.name) {
                    /* The device that is currently selected has just been removed */
                    portsList.close(/* force = */ true)
                }

                break
            }

            case 'port-update': {
                if (!portsList) {
                    break
                }

                portsList.updateUIAsap()

                if (portForm && portForm.getPortId() === event.params.id) {
                    /* Don't show field changed warnings for events that are consequences of changes applied from this
                     * client (when the event is expected) */
                    portForm.updateUI(/* fieldChangeWarnings = */ !event.expected && !portForm.inProgress())
                }

                break
            }

            case 'port-add': {
                if (!portsList) {
                    break
                }

                portsList.updateUIAsap()

                break
            }

            case 'port-remove': {
                if (!portsList) {
                    break
                }

                portsList.updateUIAsap()

                if (portForm && portForm.getPortId() === event.params.id) {
                    /* The port that is currently selected has just been removed */
                    portForm.close(/* force = */ true)
                }

                break
            }

            case 'value-change': {
                if (!portForm) {
                    break
                }

                if (event.expected) {
                    if (portForm && (portForm.getPortId() === event.params.id) && portForm.isWaitingValueChanged()) {
                        portForm.clearWaitingValueChanged()
                    }

                    break
                }

                /* Update port form */
                if (portForm && (portForm.getPortId() === event.params.id) && (event.params.value != null)) {
                    let lastSync = Math.round(new Date().getTime() / 1000)

                    let valueField = portForm.getField('value')
                    let data = {}
                    if (portForm.getField('attr_last_sync')) {
                        data['attr_last_sync'] = API.STD_PORT_ATTRDEFS['last_sync'].valueToUI(lastSync)
                    }
                    if (valueField && (valueField.getValue() !== event.params.value)) {
                        if (valueField.isReadonly() || valueField.getValue() == null) {
                            data['value'] = event.params.value
                        }
                        else {
                            if (!valueField.hasWarning() && !valueField.hasError()) {
                                valueField.setWarning(gettext('Value has been updated in the meantime.'))
                            }
                        }
                    }

                    if (Object.keys(data).length) {
                        portForm.setData(data)
                    }
                }

                break
            }

        }
    }

    makeMainPage() {
        if (API.getCurrentAccessLevel() < API.ACCESS_LEVEL_ADMIN) {
            return
        }

        if (Config.slavesEnabled) {
            return this.makeDevicesList()
        }
        else {
            return this.makePortsList()
        }
    }

}

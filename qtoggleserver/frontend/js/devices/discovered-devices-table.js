
import {gettext}             from '$qui/base/i18n.js'
import Timer                 from '$qui/base/timer.js'
import FormButton            from '$qui/forms/form-button.js'
import {CheckField}          from '$qui/forms/common-fields/common-fields.js'
import {PasswordField}       from '$qui/forms/common-fields/common-fields.js'
import {TextField}           from '$qui/forms/common-fields/common-fields.js'
import {OptionsForm}         from '$qui/forms/common-forms/common-forms.js'
import StockIcon             from '$qui/icons/stock-icon.js'
import {ANIMATION_SPIN}      from '$qui/icons/icons.js'
import {SimpleMessageForm}   from '$qui/messages/common-message-forms/common-message-forms.js'
import {PushButtonTableCell} from '$qui/tables/common-cells/common-cells.js'
import {SimpleTableCell}     from '$qui/tables/common-cells/common-cells.js'
import {PageTable}           from '$qui/tables/common-tables/common-tables.js'
import * as ArrayUtils       from '$qui/utils/array.js'

import * as MasterSlaveAPI from '$app/api/master-slave.js'
import * as Cache          from '$app/cache.js'
import * as Utils          from '$app/utils.js'

import * as Devices from './devices.js'


const DISCOVER_SCAN_TIMEOUT = 15
const DEFAULT_USE_IP_ADDRESSES = false

const logger = Devices.logger


class DiscoveredDevicesTableOptionsForm extends OptionsForm {

    constructor(discoveredDevicesTable) {
        let mainDevice = Cache.getMainDevice()
        let defaultTargetWiFiSSID = mainDevice['wifi_ssid'] || ''
        let defaultTargetWiFiPSK = mainDevice['wifi_psk'] || ''

        super({
            page: discoveredDevicesTable,
            fields: [
                new TextField({
                    name: 'target_wifi_ssid',
                    label: gettext('Target Wi-Fi Network'),
                    description: gettext('The name of the Wi-Fi network to be used by adopted devices.'),
                    maxLength: 32,
                    continuousChange: false,
                    required: true
                }),
                new PasswordField({
                    name: 'target_wifi_key',
                    label: gettext('Target Wi-Fi Key'),
                    description: gettext('The key (password) of the Wi-Fi network to be used by adopted devices.'),
                    maxLength: 64,
                    continuousChange: false,
                    revealOnFocus: true
                }),
                new CheckField({
                    name: 'use_ip_addresses',
                    label: gettext('Use IP Addresses'),
                    description: gettext('Use IP addresses instead of hostnames when adopting devices (on networks ' +
                                         'with missing local DNS resolving).'),
                    separator: true
                }),
                new CheckField({
                    name: 'use_custom_password',
                    label: gettext('Use Custom Password'),
                    description: gettext('Set a custom password instead of the hub auto-generated one on adopted ' +
                                         'devices.')
                }),
                new PasswordField({
                    name: 'custom_password',
                    label: gettext('Custom Password'),
                    maxLength: 32,
                    continuousChange: false,
                    revealOnFocus: true
                })
            ],
            buttons: [
                new FormButton({
                    id: 'refresh',
                    caption: gettext('Refresh'),
                    icon: new StockIcon({name: 'sync'})
                })
            ],
            initialData: {
                target_wifi_ssid: Cache.getPrefs('devices.target_wifi_ssid', defaultTargetWiFiSSID),
                target_wifi_key: Cache.getPrefs('devices.target_wifi_key', defaultTargetWiFiPSK),
                use_ip_addresses: Cache.getPrefs('devices.use_ip_addresses', DEFAULT_USE_IP_ADDRESSES),
                use_custom_password: Cache.getPrefs('devices.use_custom_password', false),
                custom_password: Cache.getPrefs('devices.custom_password', '')
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

    onButtonPress(button) {
        let discoverDevicesTable = this.getPage()

        switch (button.getId()) {
            case 'refresh':
                logger.debug('refreshing discovered devices')

                MasterSlaveAPI.deleteDiscovered().then(function () {
                    return discoverDevicesTable.showDiscoveredDevices()
                }).catch(function (e) {
                    discoverDevicesTable.setError(e)
                })

                discoverDevicesTable.closeOptionsBar()

                break
        }
    }

    _updateFieldsVisibility() {
        let customPasswordField = this.getField('custom_password')
        if (this.getUnvalidatedFieldValue('use_custom_password')) {
            customPasswordField.show()
        }
        else {
            customPasswordField.hide()
        }
    }

}


class AdoptTableCell extends PushButtonTableCell {

    constructor() {
        super({
            caption: gettext('Adopt')
        })
    }

    onClick() {
        let row = this.getRow()
        let discoveredDevicesTable = row.getTable()
        let discoveredDevice = row.getData()
        let useCustomPassword = Cache.getPrefs('devices.use_custom_password', false)

        // TODO: check discovered device type, since not all types will require Wi-Fi settings in the future
        if (!Cache.getPrefs('devices.target_wifi_ssid')) {
            new SimpleMessageForm({
                type: 'info',
                message: gettext('Please use the options panel to fill out target Wi-Fi settings.')
            }).show()

            return
        }

        let mainDevice = Cache.getMainDevice()
        if (!mainDevice['admin_password'] && !useCustomPassword) {
            new SimpleMessageForm({
                type: 'warning',
                message: gettext("You don't have an administrator password. Please set one before adopting devices.")
            }).show()

            return
        }

        this.setIcon(new StockIcon({name: 'sync', animation: ANIMATION_SPIN}))
        this.setEnabled(false)
        this.setCaption(gettext('Adopting...'))

        discoveredDevicesTable.adoptDevice(discoveredDevice).catch(() => {}).then(function () {
            discoveredDevicesTable.removeRow(row)
        })
    }

}


/**
 * @alias qtoggle.devices.DiscoveredDevicesTable
 * @extends qui.tables.commontables.PageTable
 */
class DiscoveredDevicesTable extends PageTable {

    /**
     * @constructs
     */
    constructor() {
        super({
            icon: Devices.DEVICE_ICON,
            title: gettext('Discovered Devices'),
            pathId: 'discover',
            selectMode: 'disabled',
            searchEnabled: true,
            header: [gettext('Display Name'), gettext('Name'), 'Actions'],
            rowTemplate: [SimpleTableCell, SimpleTableCell, AdoptTableCell]
        })
    }

    load() {
        return this.showDiscoveredDevices()
    }

    showDiscoveredDevices() {
        this.setProgress(0)
        this.setProgressMessage(gettext('Discovering devices...'))

        logger.debug('starting device discovery')

        let discoverStep = 0
        let discoverSteps = DISCOVER_SCAN_TIMEOUT * 1000 / 100
        let discoverTimer = new Timer(100, function () {

            discoverStep++
            let discoverProgress = discoverStep * 100 / discoverSteps
            if (discoverProgress <= 100) {
                this.setProgress(discoverProgress)
            }
            else {
                this.setProgress(null)
            }

        }.bind(this), /* repeat = */ true)

        discoverTimer.start()

        this.setRows([])

        return MasterSlaveAPI.getDiscovered(DISCOVER_SCAN_TIMEOUT).then(function (discoveredDevices) {

            logger.debug(`discovered ${discoveredDevices.length} devices`)
            ArrayUtils.sortKey(discoveredDevices, d => (d.attrs['display_name'] || d.attrs['name']))
            discoveredDevices.forEach(function (d) {

                this.addRowValues(-1, [d.attrs['display_name'], d.attrs['name']], /* data = */ d)

            }.bind(this))

        }.bind(this)).catch(function (e) {

            logger.errorStack('device discovery failed', e)
            this.setError(e.toString())

        }.bind(this)).then(function () {

            discoverTimer.cancel()
            this.clearProgress()

        }.bind(this))
    }

    adoptDevice(discoveredDevice) {
        let name = discoveredDevice.attrs['name']
        logger.debug(`adopting device ${name}`)

        let useIPAddresses = Cache.getPrefs('devices.use_ip_addresses', DEFAULT_USE_IP_ADDRESSES)
        let useCustomPassword = Cache.getPrefs('devices.use_custom_password', false)
        let customPassword = Cache.getPrefs('devices.custom_password', '')

        let attrs = {
            wifi_ssid: Cache.getPrefs('devices.target_wifi_ssid'),
            wifi_key: Cache.getPrefs('devices.target_wifi_key')
        }

        if (useCustomPassword) {
            attrs['admin_password'] = customPassword
            if ('normal_password' in discoveredDevice.attrs) {
                attrs['normal_password'] = customPassword
            }
            if ('viewonly_password' in discoveredDevice.attrs) {
                attrs['viewonly_password'] = customPassword
            }
        }

        let promise = MasterSlaveAPI.patchDiscoveredDevice(discoveredDevice.attrs['name'], attrs)
        return promise.then(function (patchedDiscoveredDevice) {

            logger.debug(`successfully updated device ${name}`)
            return MasterSlaveAPI.postSlaveDevices(
                patchedDiscoveredDevice.scheme,
                useIPAddresses ? patchedDiscoveredDevice.ip_address : patchedDiscoveredDevice.hostname,
                patchedDiscoveredDevice.port,
                patchedDiscoveredDevice.path,
                patchedDiscoveredDevice.admin_password
            )

        }).then(function () {

            logger.debug(`successfully added device ${name}`)

        }).catch(function (error) {

            logger.errorStack(`failed to adopt device ${name}`, error)
            Utils.showToastError(error)
            throw error

        })
    }

    makeOptionsBarContent() {
        return new DiscoveredDevicesTableOptionsForm(this)
    }

    onClose() {
        MasterSlaveAPI.deleteDiscovered()
    }

}


export default DiscoveredDevicesTable

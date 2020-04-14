/**
 * @namespace qtoggle.api.attrdefs
 */

import {gettext}           from '$qui/base/i18n.js'
import {PasswordField}     from '$qui/forms/common-fields.js'
import {ProgressDiskField} from '$qui/forms/common-fields.js'
import {TextAreaField}     from '$qui/forms/common-fields.js'
import {TextField}         from '$qui/forms/common-fields.js'
import * as DateUtils      from '$qui/utils/date.js'
import * as ObjectUtils    from '$qui/utils/object.js'

import {netmaskFromLen} from '$app/utils.js'
import {netmaskToLen}   from '$app/utils.js'

import {WiFiSignalStrengthField} from './attrdef-fields.js'


const IP_ADDRESS_PATTERN = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/


/**
 * @alias qtoggle.api.attrdefs.STD_DEVICE_ATTRDEFS
 * @type {Object}
 */
export const STD_DEVICE_ATTRDEFS = {
    name: {
        display_name: gettext('Device Name'),
        description: gettext('The name of the device.'),
        type: 'string',
        max: 32,
        required: true,
        modifiable: true,
        regex: '^[_a-zA-Z][_a-zA-Z0-9-]*$',
        standard: true,
        separator: true,
        order: 100
    },
    display_name: {
        display_name: gettext('Display Name'),
        description: gettext('A friendly name to be used when showing the device.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
        order: 110
    },
    version: {
        display_name: gettext('Firmware Version'),
        description: gettext('The current version of the firmware.'),
        type: 'string',
        modifiable: false,
        standard: true,
        order: 120
    },
    api_version: {
        display_name: gettext('API Version'),
        description: gettext('The API version implemented by the device.'),
        type: 'string',
        modifiable: false,
        standard: true,
        order: 130
    },
    vendor: {
        display_name: gettext('Vendor'),
        description: gettext('The implementation vendor.'),
        type: 'string',
        modifiable: false,
        standard: true,
        order: 140
    },
    admin_password: {
        display_name: gettext('Administrator Password'),
        description: gettext("The administrator's password, required to perform administrative tasks."),
        type: 'string',
        max: 32,
        modifiable: true,
        standard: true,
        showAnyway: true,
        separator: true,
        order: 150,
        field: {
            class: PasswordField,
            autocomplete: false,
            clearEnabled: true,
            clearPlaceholder: true,
            placeholder: `(${gettext('hidden')})`
        }
    },
    normal_password: {
        display_name: gettext('Normal Password'),
        description: gettext("The normal user's password, required to perform regular tasks."),
        type: 'string',
        max: 32,
        optional: true,
        modifiable: true,
        standard: true,
        showAnyway: true,
        order: 151,
        field: {
            class: PasswordField,
            autocomplete: false,
            clearEnabled: true,
            clearPlaceholder: true,
            placeholder: `(${gettext('hidden')})`
        }
    },
    viewonly_password: {
        display_name: gettext('View-only Password'),
        description: gettext("The view-only user's password required for view-only privileges."),
        type: 'string',
        max: 32,
        optional: true,
        modifiable: true,
        standard: true,
        showAnyway: true,
        order: 152,
        field: {
            class: PasswordField,
            autocomplete: false,
            clearEnabled: true,
            clearPlaceholder: true,
            placeholder: `(${gettext('hidden')})`
        }
    },
    date: {
        display_name: gettext('System Date/Time'),
        description: gettext("The current system date and time, in your app's timezone."),
        type: 'string',
        modifiable: true,
        optional: true,
        standard: true,
        separator: true,
        order: 160,
        valueToUI: v => DateUtils.formatPercent(new Date(v * 1000), '%Y-%m-%d %H:%M:%S'),
        valueFromUI: v => Math.round(Date.parse(v) / 1000),
        field: {
            class: TextField,
            autocomplete: false,
            pattern: DATE_PATTERN
        }
    },
    timezone: {
        display_name: gettext('Timezone'),
        description: gettext('The device timezone.'),
        type: 'string',
        modifiable: true,
        optional: true,
        standard: true,
        separator: false,
        order: 161
    },
    uptime: {
        display_name: gettext('Uptime'),
        description: gettext('The number of seconds passed since the device has been turned on.'),
        type: 'number',
        unit: gettext('seconds'),
        integer: true,
        modifiable: false,
        optional: true,
        standard: true,
        order: 162
    },
    wifi_ssid: {
        display_name: gettext('Wi-Fi Network'),
        description: gettext('Your Wi-Fi network name. Leave empty when not using Wi-Fi.'),
        separator: true,
        type: 'string',
        modifiable: true,
        reconnect: true,
        max: 32,
        optional: true,
        standard: true,
        order: 170
    },
    wifi_key: {
        display_name: gettext('Wi-Fi Key'),
        description: gettext('Your Wi-Fi network key (password). Leave empty for an open Wi-Fi network.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        max: 64,
        optional: true,
        standard: true,
        order: 171,
        field: {
            class: PasswordField,
            autocomplete: false,
            clearEnabled: true,
            revealOnFocus: true
        }
    },
    wifi_bssid: {
        display_name: gettext('Wi-Fi BSSID'),
        description: gettext('A specific BSSID (MAC address) of a Wi-Fi access point. ' +
                             'Leave empty for automatic selection.'),
        regex: '^[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}:[a-fA-F0-9]{2}$',
        type: 'string',
        modifiable: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 172,
        field: {
            class: TextField,
            autocomplete: false,
            clearEnabled: true,
            placeholder: 'AA:BB:CC:DD:EE:FF'
        }
    },
    wifi_bssid_current: {
        display_name: gettext('Wi-Fi BSSID (Current)'),
        description: gettext('The BSSID (MAC address) of the access point to which the device is currently connected.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 173
    },
    wifi_signal_strength: {
        display_name: gettext('Wi-Fi Strength'),
        description: gettext('Indicates the quality of the Wi-Fi connection.'),
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 174,
        field: {
            class: WiFiSignalStrengthField
        }
    },
    ip_address: {
        display_name: gettext('IP Address'),
        description: gettext('Manually configured IP address. Leave empty for automatic (DHCP) configuration.'),
        separator: true,
        type: 'string',
        modifiable: true,
        reconnect: true,
        regex: '^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',
        optional: true,
        standard: true,
        order: 180,
        field: {
            class: TextField,
            autocomplete: false,
            placeholder: '192.168.1.2',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_netmask: {
        display_name: gettext('Network Mask'),
        description: gettext('Manually configured network mask. Leave empty for automatic (DHCP) configuration.'),
        type: 'number',
        modifiable: true,
        min: 0,
        max: 31,
        integer: true,
        reconnect: true,
        optional: true,
        standard: true,
        order: 181,
        valueToUI: v => v ? netmaskFromLen(v) : '',
        valueFromUI: v => v ? netmaskToLen(v) : 0,
        field: {
            class: TextField,
            autocomplete: false,
            placeholder: '255.255.255.0',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_gateway: {
        display_name: gettext('Gateway'),
        description: gettext('Manually configured gateway (default route). ' +
                             'Leave empty for automatic (DHCP) configuration.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        regex: '^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',
        optional: true,
        standard: true,
        order: 182,
        field: {
            class: TextField,
            autocomplete: false,
            placeholder: '192.168.1.1',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_dns: {
        display_name: gettext('DNS Server'),
        description: gettext('Manually configured DNS server. Leave empty for automatic (DHCP) configuration.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        regex: '^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',
        optional: true,
        standard: true,
        order: 183,
        field: {
            class: TextField,
            autocomplete: false,
            placeholder: '192.168.1.1',
            pattern: IP_ADDRESS_PATTERN
        }
    },
    ip_address_current: {
        display_name: gettext('IP Address (Current)'),
        description: gettext('The current IP address of the device.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 184
    },
    ip_netmask_current: {
        display_name: gettext('Network Mask (Current)'),
        description: gettext('The current network mask of the device.'),
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        valueToUI: v => v ? netmaskFromLen(v) : '',
        field: {
            class: TextField
        },
        order: 185
    },
    ip_gateway_current: {
        display_name: gettext('Gateway (Current)'),
        description: gettext('The current gateway (default route) of the device.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 186
    },
    ip_dns_current: {
        display_name: gettext('DNS Server (Current)'),
        description: gettext('The current DNS server of the device.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 187
    },
    cpu_usage: {
        display_name: gettext('CPU Usage'),
        description: gettext('The total CPU usage.'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 190,
        field: {
            class: ProgressDiskField,
            color: '@red-color'
        }
    },
    mem_usage: {
        display_name: gettext('Memory Usage'),
        description: gettext('The current RAM usage.'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 191,
        field: {
            class: ProgressDiskField,
            color: '@green-color'
        }
    },
    storage_usage: {
        display_name: gettext('Storage Usage'),
        description: gettext('The storage (disk/flash) usage.'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 192,
        field: {
            class: ProgressDiskField,
            color: '@blue-color'
        }
    },
    battery_level: {
        display_name: gettext('Battery Level'),
        description: gettext('The battery state of charge level.'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 193,
        field: {
            class: ProgressDiskField,
            color: '@orange-color'
        }
    },
    temperature: {
        display_name: gettext('Temperature'),
        description: gettext('The current device (core) temperature.'),
        unit: '\xb0C',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 194
    },
    low_battery: {
        display_name: gettext('Low Battery'),
        description: gettext('Indicates that battery is low and must be replaced or charged.'),
        type: 'boolean',
        modifiable: false,
        optional: true,
        standard: true,
        order: 195
    },
    flags: {
        display_name: gettext('Device Features'),
        description: gettext('Device flags that indicate support for various optional functions.'),
        separator: true,
        type: 'flags', // TODO replace with list of strings
        standard: true,
        order: 200
    },
    config_name: {
        display_name: gettext('Configuration Name'),
        description: gettext('Indicates a particular device configuration.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 210
    },
    virtual_ports: {
        display_name: gettext('Virtual Ports'),
        description: gettext('Indicates the number of virtual ports supported by the device.'),
        type: 'number',
        integer: 'true',
        modifiable: false,
        optional: true,
        standard: true,
        order: 220
    }
}

/**
 * @alias qtoggle.api.attrdefs.ADDITIONAL_DEVICE_ATTRDEFS
 * @type {Object}
 */
export const ADDITIONAL_DEVICE_ATTRDEFS = {
}

/**
 * @alias qtoggle.api.attrdefs.STD_PORT_ATTRDEFS
 * @type {Object}
 */
export const STD_PORT_ATTRDEFS = {
    id: {
        display_name: gettext('Port Identifier'),
        description: gettext('The unique identifier of the port.'),
        type: 'string',
        max: 64,
        modifiable: false,
        regex: '^[_a-zA-Z][._a-zA-Z0-9-]*$',
        standard: true,
        order: 100
    },
    enabled: {
        display_name: gettext('Enabled'),
        description: gettext('Enables or disables the port.'),
        type: 'boolean',
        modifiable: true,
        standard: true,
        order: 110
    },
    online: {
        display_name: gettext('Online'),
        description: gettext('Indicates if the port is online or not.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        optional: true,
        order: 120
    },
    last_sync: {
        display_name: gettext('Last Sync'),
        description: gettext('The last time when the value of this port has been updated.'),
        type: 'string',
        modifiable: false,
        standard: true,
        valueToUI: function (value) {
            if (value == null || value < 0) {
                return `(${gettext('never')})`
            }
            else {
                return DateUtils.formatPercent(new Date(value * 1000), '%Y-%m-%d %H:%M:%S')
            }
        },
        order: 130
    },
    expires: {
        display_name: gettext('Expires'),
        description: gettext('The number of seconds before the port value is considered expired. 0 means ' +
                             'that port value never expires.'),
        unit: gettext('seconds'),
        type: 'number',
        modifiable: true,
        standard: true,
        min: 0,
        max: 2147483647,
        integer: true,
        order: 140
    },
    type: {
        display_name: gettext('Type'),
        description: gettext('The type of the port value.'),
        type: 'string',
        choices: [
            {display_name: gettext('Boolean'), value: 'boolean'},
            {display_name: gettext('Number'), value: 'number'}
        ],
        modifiable: false,
        separator: true,
        standard: true,
        order: 150
    },
    display_name: {
        display_name: gettext('Display Name'),
        description: gettext('A friendly name to be used when showing the port.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
        order: 160
    },
    unit: {
        display_name: gettext('Unit'),
        description: gettext('The unit of measurement for the value of this port.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
        optional: true,
        order: 170
    },
    writable: {
        display_name: gettext('Writable'),
        description: gettext('Tells if values can be written to the port.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        order: 180
    },
    persisted: {
        display_name: gettext('Persist Value'),
        description: gettext('Controls whether the port value is preserved and restored when device is restarted.'),
        type: 'boolean',
        modifiable: true,
        standard: true,
        optional: true,
        order: 190
    },
    min: {
        display_name: gettext('Minimum Value'),
        description: gettext('The minimum accepted value for this port.'),
        type: 'number',
        modifiable: false,
        separator: true,
        standard: true,
        optional: true,
        order: 200
    },
    max: {
        display_name: gettext('Maximum Value'),
        description: gettext('The maximum accepted value for this port.'),
        type: 'number',
        modifiable: false,
        standard: true,
        optional: true,
        order: 210
    },
    integer: {
        display_name: gettext('Integer Values'),
        description: gettext('Indicates that only integer values are accepted for this port.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        optional: true,
        order: 220
    },
    step: {
        display_name: gettext('Step'),
        description: gettext("Indicates the granularity for this port's value."),
        type: 'number',
        modifiable: false,
        standard: true,
        optional: true,
        order: 230
    },
    // TODO choices
    tag: {
        display_name: gettext('Tag'),
        description: gettext('User-defined details.'),
        type: 'string',
        max: 64,
        modifiable: true,
        separator: true,
        standard: true,
        optional: true,
        order: 240
    },
    virtual: {
        display_name: gettext('Virtual Port'),
        description: gettext('Indicates that this is a virtual port.'),
        type: 'boolean',
        modifiable: false,
        standard: true,
        optional: true,
        order: 250
    },
    expression: {
        display_name: gettext('Expression'),
        description: gettext('An expression that controls the port value.'),
        type: 'string',
        max: 1024,
        modifiable: true,
        separator: true,
        standard: true,
        optional: true,
        order: 260,
        field: {
            class: TextAreaField,
            resize: 'vertical'
        }
    },
    device_expression: {
        /* display_name is added dynamically */
        description: gettext('An expression that controls the port value directly on the device.'),
        type: 'string',
        modifiable: true,
        standard: true,
        optional: true,
        max: 1024,
        field: {
            class: TextAreaField,
            resize: 'vertical'
        }
        /* order is added dynamically */
    },
    transform_write: {
        display_name: gettext('Write Transform Expression'),
        description: gettext('An expression to be applied on the value when written to the port.'),
        type: 'string',
        max: 1024,
        modifiable: true,
        standard: true,
        optional: true,
        order: 270
    },
    transform_read: {
        display_name: gettext('Read Transform Expression'),
        description: gettext('An expression to be applied on the value read from the port.'),
        type: 'string',
        max: 1024,
        modifiable: true,
        standard: true,
        optional: true,
        order: 280
    }
}

/**
 * @alias qtoggle.api.attrdefs.ADDITIONAL_PORT_ATTRDEFS
 * @type {Object}
 */
export const ADDITIONAL_PORT_ATTRDEFS = {
}

/* All standard and known additional attribute definitions have the "known" field set to true */
ObjectUtils.forEach(STD_DEVICE_ATTRDEFS, (name, def) => {
    def.known = true
})
ObjectUtils.forEach(ADDITIONAL_DEVICE_ATTRDEFS, (name, def) => {
    def.known = true
})
ObjectUtils.forEach(STD_PORT_ATTRDEFS, (name, def) => {
    def.known = true
})
ObjectUtils.forEach(ADDITIONAL_PORT_ATTRDEFS, (name, def) => {
    def.known = true
})

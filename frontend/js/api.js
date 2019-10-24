
import Logger from '$qui/lib/logger.module.js'

import {AssertionError}  from '$qui/base/errors.js'
import {gettext}         from '$qui/base/i18n.js'
import Config            from '$qui/config.js'
import * as AJAX         from '$qui/utils/ajax.js'
import * as Crypto       from '$qui/utils/crypto.js'
import * as DateUtils    from '$qui/utils/date.js'
import {asap}            from '$qui/utils/misc.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as StringUtils  from '$qui/utils/string.js'

import * as Cache from '$app/cache.js'


const DEBUG_API_CALLS = true
const DEFAULT_EXPECT_TIMEOUT = 60 /* Seconds */
const ROUND_VALUE_TEMPLATE = 1e6
const FAST_RECONNECT_LISTEN_ERRORS = 2

export const LISTEN_KEEPALIVE = 60 /* Seconds TODO server setting */
export const SERVER_RETRY_INTERVAL = 3 /* Seconds TODO server setting */
export const SERVER_TIMEOUT = 15 /* Seconds TODO server setting */

export const ACCESS_LEVEL_ADMIN = 30
export const ACCESS_LEVEL_NORMAL = 20
export const ACCESS_LEVEL_VIEWONLY = 10
export const ACCESS_LEVEL_NONE = 0

export const ACCESS_LEVEL_MAPPING = {
    admin: ACCESS_LEVEL_ADMIN,
    normal: ACCESS_LEVEL_NORMAL,
    viewonly: ACCESS_LEVEL_VIEWONLY,
    none: ACCESS_LEVEL_NONE,
    unknown: null
}

export const FIRMWARE_STATUS_IDLE = 'idle'
export const FIRMWARE_STATUS_CHECKING = 'checking'
export const FIRMWARE_STATUS_DOWNLOADING = 'downloading'
export const FIRMWARE_STATUS_EXTRACTING = 'extracting'
export const FIRMWARE_STATUS_VALIDATING = 'validating'
export const FIRMWARE_STATUS_FLASHING = 'flashing'
export const FIRMWARE_STATUS_RESTARTING = 'restarting'
export const FIRMWARE_STATUS_ERROR = 'error'

const QTOGGLE_API_PREFIX = '/api'


/* Reverse mapping */
ObjectUtils.forEach(ACCESS_LEVEL_MAPPING, function (k, v) {
    ACCESS_LEVEL_MAPPING[v] = k
})

export const STD_DEVICE_ATTRDEFS = {
    name: {
        display_name: gettext('Device Name'),
        description: gettext('The name of the device.'),
        type: 'string',
        max: 32,
        required: true,
        modifiable: true,
        regex: '^[_a-zA-Z][_a-zA-Z0-9]*$',
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
    uptime: {
        display_name: gettext('Uptime'),
        description: gettext('The number of seconds passed since the device has been turned on.'),
        type: 'number',
        unit: gettext('seconds'),
        integer: true,
        modifiable: false,
        optional: true,
        standard: true,
        order: 150
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
        order: 160
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
        order: 170
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
        order: 180
    },
    date: {
        display_name: gettext('System Date/Time'),
        description: gettext('The current system date and time.'),
        type: 'string',
        modifiable: true,
        regex: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$',
        optional: true,
        standard: true,
        separator: true,
        order: 190
    },
    timezone: {
        display_name: gettext('Timezone'),
        description: gettext('The device timezone.'),
        type: 'string',
        modifiable: true,
        optional: true,
        standard: true,
        separator: false,
        order: 200
    },
    network_wifi: {
        display_name: gettext('WiFi Configuration'),
        description: gettext('The device WiFi configuration.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        // TODO this regex should ignore escaped colons \:
        regex: '^(([^:]{0,32}:?)|([^:]{0,32}:[^:]{0,64}:?)|([^:]{0,32}:[^:]{0,64}:[0-9a-fA-F]{12}))$',
        optional: true,
        standard: true,
        order: 210
    },
    network_ip: {
        display_name: gettext('IP Configuration'),
        description: gettext('The device network IP configuration.'),
        type: 'string',
        modifiable: true,
        reconnect: true,
        regex: ('^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}/\\d{1,2}:' +
                '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}:' +
                '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$'),
        optional: true,
        standard: true,
        order: 220
    },
    battery_level: {
        display_name: gettext('Battery Level'),
        description: gettext('The battery charge level.'),
        unit: '%',
        type: 'number',
        modifiable: false,
        optional: true,
        standard: true,
        order: 230
    },
    low_battery: {
        display_name: gettext('Low Battery'),
        description: gettext('Indicates that battery is low and must be replaced or charged.'),
        type: 'boolean',
        modifiable: false,
        optional: true,
        standard: true,
        order: 240
    },
    flags: {
        display_name: gettext('Device Features'),
        description: gettext('Device flags that indicate support for various optional functions.'),
        type: 'flags', // TODO replace with list of strings
        standard: true,
        order: 250
    },
    virtual_ports: {
        display_name: gettext('Virtual Ports'),
        description: gettext('Indicates the number of virtual ports supported by the device.'),
        type: 'number',
        integer: 'true',
        modifiable: false,
        optional: true,
        standard: true,
        order: 260
    },
    config_name: {
        display_name: gettext('Configuration Name'),
        description: gettext('Indicates a particular device configuration.'),
        type: 'string',
        modifiable: false,
        optional: true,
        standard: true,
        order: 270
    }
}

export const ADDITIONAL_DEVICE_ATTRDEFS = {
}

export const STD_PORT_ATTRDEFS = {
    id: {
        display_name: gettext('Port Identifier'),
        description: gettext('The unique identifier of the port.'),
        type: 'string',
        max: 64,
        modifiable: false,
        regex: '^[_a-zA-Z][._a-zA-Z0-9]*$',
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
        description: gettext('The unit of measurement for this port.'),
        type: 'string',
        max: 64,
        modifiable: true,
        standard: true,
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
        order: 260
    },
    device_expression: {
        /* display_name is added dynamically */
        description: gettext('An expression that controls the port value directly on the device.'),
        type: 'string',
        modifiable: true,
        standard: true,
        optional: true,
        max: 1024
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

const KNOWN_ERRORS = [
    /* HTTP 400 */
    {
        status: 400,
        rex: new RegExp('^malformed request$'),
        pretty: StringUtils.formatPercent(
            gettext('Communication protocol error (%(error)s).'),
            {error: 'malformed request'}
        )
    },
    {
        status: 400,
        rex: new RegExp('^malformed body'),
        pretty: StringUtils.formatPercent(
            gettext('Communication protocol error (%(error)s).'),
            {error: 'malformed body'}
        )
    },
    {
        status: 400,
        rex: new RegExp('^missing field: (\\w+)$'),
        pretty: StringUtils.formatPercent(
            gettext('Communication protocol error (%(error)s).'),
            {error: 'missing field "$1"'}
        )
    },
    {
        status: 400,
        rex: new RegExp('^invalid request$'),
        pretty: StringUtils.formatPercent(
            gettext('Communication protocol error (%(error)s).'),
            {error: 'invalid request'}
        )
    },
    {
        status: 400,
        rex: new RegExp('^attribute not modifiable: (\\w+)$'),
        pretty: StringUtils.formatPercent(gettext('Attribute "%(attr)s" is not modifiable.'), {attr: '$1'})
    },
    {
        status: 400,
        rex: new RegExp('^no such attribute: (\\w+)$'),
        pretty: StringUtils.formatPercent(gettext('No such attribute "%(attr)s".'), {attr: '$1'})
    },
    {
        status: 400,
        rex: new RegExp('^invalid field: (\\w+)$'),
        pretty: StringUtils.formatPercent(gettext('Invalid value for "%(field)s".'), {field: '$1'})
    },
    {
        status: 400,
        rex: new RegExp('^no such version$'),
        pretty: gettext('Firmware version not available.')
    },
    {
        status: 400,
        rex: new RegExp('^duplicate port$'),
        pretty: gettext('The port already exists.')
    },
    {
        status: 400,
        rex: new RegExp('^too many ports$'),
        pretty: gettext('The maximum number of ports has been reached.')
    },
    {
        status: 400,
        rex: new RegExp('^port not removable$'),
        pretty: gettext('Ports that are not virtual cannot be removed.')
    },
    {
        status: 400,
        rex: new RegExp('^port disabled$'),
        pretty: gettext('Requested operation needs the port to be enabled.')
    },
    {
        status: 400,
        rex: new RegExp('^read-only port$'),
        pretty: gettext('Requested operation needs the port to be writable.')
    },
    {
        status: 400, /* Generated by slave devices */
        rex: new RegExp('^forbidden$'),
        pretty: gettext('The supplied credentials are incorrect.')
    },
    {
        status: 400,
        rex: new RegExp('^duplicate device$'),
        pretty: gettext('The device has already been added to master.')
    },
    {
        status: 400,
        rex: new RegExp('^no listen support$'),
        pretty: gettext('The device does not support listening.')
    },
    {
        status: 400,
        rex: new RegExp('^listening and polling$'),
        pretty: gettext('Listening and polling cannot be both enabled.')
    },

    /* HTTP 401 */
    {
        status: 401,
        rex: new RegExp('^authentication required$'),
        pretty: gettext('Credentials are required.')
    },

    /* HTTP 403 */
    {
        status: 403,
        rex: new RegExp('^forbidden$'),
        pretty: gettext('The supplied credentials are incorrect.')
    },

    /* HTTP 404 */
    {
        status: 404,
        rex: new RegExp('^no such port$'),
        pretty: gettext('Requested port does not exist.')
    },
    {
        status: 404,
        rex: new RegExp('^no such function$'),
        pretty: gettext("Device doesn't support the QToggle API.")
    },
    {
        status: 404,
        rex: new RegExp('^no such device$'),
        pretty: gettext('Requested device does not exist.')
    },
    {
        status: 404,
        rex: new RegExp('^device disabled$'),
        pretty: gettext('Requested device is disabled.')
    },

    /* HTTP 502 */
    {
        status: 502,
        rex: new RegExp('^port error: (\\w+)$'),
        pretty: StringUtils.formatPercent(gettext('Port communication error: %(error)s.'), {error: '$1'})
    },
    {
        status: 502,
        rex: new RegExp('^invalid device$'),
        pretty: gettext('The device is not a QToggle device.')
    },
    {
        status: 502,
        rex: new RegExp('^connection refused$'),
        pretty: gettext('Device refuses the connection.')
    },
    {
        status: 502,
        rex: new RegExp('^unreachable$'),
        pretty: gettext('Device is unreachable.')
    },

    /* HTTP 503 */
    {
        status: 503,
        rex: new RegExp('^busy$'),
        pretty: gettext('Device is busy.')
    },
    {
        status: 503,
        rex: new RegExp('^device offline$'),
        pretty: gettext('Device is offline.')
    },

    /* HTTP 504 */
    {
        status: 504,
        rex: new RegExp('^port timeout$'),
        pretty: gettext('Timeout while communicating with the port.')
    },
    {
        status: 504,
        rex: new RegExp('^device timeout$'),
        pretty: gettext('Timeout waiting for a response from the device.')
    },

    /* Other errors */
    {
        rex: new RegExp('^timeout$'),
        pretty: gettext('Timeout waiting for a response from the device.')
    },
    {
        rex: new RegExp('^other error: (.*)$'),
        pretty: StringUtils.formatPercent(gettext('Error communicating with device (%(error)s).'), {error: '$1'})
    }
]

const logger = Logger.get('qtoggle.api')


/* Credentials & rights */

/**
 * Access level change callback.
 * @callback QToggle.API.AccessLevelChangeCallback
 * @param {Number} oldLevel the old access level
 * @param {Number} newLevel the new access level
 */

let currentUsername = null
let currentPasswordHash = null
let currentAccessLevel = null
let accessLevelChangeListeners = []


/* Notifications */

/**
 *
 * @class QToggle.API.Event
 * @classdesc A qToggle event
 * @param {String} type the event type
 * @param {Object} params the event parameters
 * @param {Boolean} [expected] indicates that the event was expected
 */
export class Event {

    constructor(type, params, expected) {
        this.type = type
        this.params = ObjectUtils.copy(params)
        this.expected = expected
    }


    /**
     * Clones the event.
     * @returns {QToggle.API.Event} the cloned event
     */
    clone() {
        return new Event(this.type, this.params, this.expected)
    }

}

let eventListeners = []
let expectedEventSpecs = {}
let expectedEventLastHandle = 0
let sessionId = null
let listeningTime = null
let listenWaiting = false
let listenErrorCount = 0

/* Flag used during firmware update */
let ignoreListenErrors = false


/* Synchronization feedback */

let syncListenError = null
let syncBeginCallbacks = []
let syncEndCallbacks = []
let syncListenCallbacks = []


/* Other API parameters */

let slaveName = null
let apiURLPrefix = ''


/**
 * @class QToggle.API.APIError
 * @classdesc An API error.
 * @param {Object} [params]
 */
export class APIError extends Error {

    constructor({msg, status, pretty = '', knownError = null, params = []}) {
        super(msg)

        this.msg = msg
        this.status = status
        this.pretty = pretty
        this.knownError = knownError
        this.params = params
    }

    toString() {
        return this.pretty || this.msg || `APIError ${this.status}`
    }

}

function parseAPIErrorMessage(status, message) {
    let parsed = null

    /* Messages starting with "other error: " may encapsulate themselves a known error;
     * we therefore pass the remaining part of the message through the parsing function again */
    let match = message.match(new RegExp('^other error: (.*)$'))
    if (match) {
        parsed = parseAPIErrorMessage(status, match[1])
        if (parsed) {
            return parsed
        }
    }

    KNOWN_ERRORS.some(function (e) {
        let match = message.match(e.rex)
        if (match && (!e.status || e.status === status)) {
            e = ObjectUtils.copy(e, /* deep = */ true)
            match.forEach(function (m, i) {
                if (i === 0) {
                    return /* Skip global group */
                }
                /* This allows no more than 9 match groups! */
                e.pretty = StringUtils.replaceAll(e.pretty, `$${i}`, m)
            })
            e.params = match.slice(1)
            parsed = e

            return true
        }
    })

    return parsed
}

function makeRequestJWT(username, passwordHash) {
    let jwtHeader = {typ: 'JWT', alg: 'HS256'}
    let jwtPayload = {
        usr: username,
        iat: Math.round(new Date().getTime() / 1000),
        ori: 'consumer',
        iss: 'qToggle'
    }
    let jwtHeaderStr = Crypto.str2b64(JSON.stringify(jwtHeader))
    let jwtPayloadStr = Crypto.str2b64(JSON.stringify(jwtPayload))
    let jwtSigningString = `${jwtHeaderStr}.${jwtPayloadStr}`
    let jwtSignature = new Crypto.HMACSHA256(passwordHash, jwtSigningString).digest()
    let jwtSignatureStr = Crypto.str2b64(Crypto.arr2str(jwtSignature))

    return `${jwtSigningString}.${jwtSignatureStr}`
}

/**
 * Call an API function.
 * @memberof QToggle.API
 * @param {Object} params
 * @param {String} params.method the method
 * @param {String} params.path the path (URI)
 * @param {?Object} [params.query] optional query arguments
 * @param {?Object} [params.data] optional data (body)
 * @param {?Number} [params.timeout] timeout, in seconds
 * @param {?Number} [params.expectedHandle] the handle of the expected event
 * @param {Boolean} [params.handleErrors] set to `false` to prevent error handling (defaults to `true`)
 * @returns {Promise} a promise that is resolved when the API call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function apiCall({
    method, path, query = null, data = null, timeout = SERVER_TIMEOUT, expectedHandle = null, handleErrors = true
}) {

    return new Promise(function (resolve, reject) {
        let apiFuncPath = path

        if (slaveName) { /* Slave QToggle API call */
            path = `/devices/${slaveName}/forward${path}`
            slaveName = null
        }

        path = QTOGGLE_API_PREFIX + path

        let isListen = apiFuncPath.startsWith('/listen')
        if (apiURLPrefix) {
            path = apiURLPrefix + path
        }

        if (method === 'POST' || method === 'PATCH' || method === 'PUT') {
            if (DEBUG_API_CALLS && data != null) {
                let bodyStr = JSON.stringify(data, null, 4).replace(new RegExp('\\n', 'g'), '\n   ')
                logger.debug(`call "${method} ${apiFuncPath}":\n    ${bodyStr}`)
            }
            else {
                logger.debug(`call "${method} ${apiFuncPath}"`)
            }
        }
        else {
            data = null
            logger.debug(`call "${method} ${apiFuncPath}"`)
        }

        query = query || {}

        function resolveWrapper(data) {
            if (!isListen) {
                syncEndCallbacks.forEach(c => PromiseUtils.asap().then(() => c()))
            }

            if (DEBUG_API_CALLS && data != null) {
                let bodyStr = JSON.stringify(data, null, 4).replace(new RegExp('\\n', 'g'), '\n   ')
                logger.debug(`response for "${method} ${apiFuncPath}": \n    ${bodyStr}`)
            }
            else {
                logger.debug(`response for "${method} ${apiFuncPath}"`)
            }

            resolve(data)
        }

        function rejectWrapper(data, status, msg) {
            let error = new APIError({
                msg: data.error || msg,
                status: status
            })

            let matchedAPIError = null
            if (data.error) {
                matchedAPIError = parseAPIErrorMessage(status, data.error)
                if (matchedAPIError) {
                    error.pretty = matchedAPIError.pretty
                    error.knownError = matchedAPIError
                    error.params = matchedAPIError.params
                }
            }

            if (status === 403) {
                let level = ACCESS_LEVEL_MAPPING[data.required_level]
                switch (level) {
                    case ACCESS_LEVEL_ADMIN:
                        error.pretty = gettext('Administrator access level required.')
                        break

                    case ACCESS_LEVEL_NORMAL:
                        error.pretty = gettext('Normal access level required.')
                        break

                    case ACCESS_LEVEL_VIEWONLY:
                        error.pretty = gettext('View-only access level required.')
                        break
                }
            }
            if (status === 500 && data && data.error) {
                /* Internal server error */
                error.pretty = gettext('Unexpected error while communicating with the server (%(error)s).')
                error.pretty = StringUtils.formatPercent(error.pretty, {error: data.error})
            }
            else if (status === 503 && data && data.error === 'busy') {
                error.pretty = gettext('The device is busy.')
            }
            else if (status === 0) {
                if (msg === 'timeout') {
                    error.pretty = gettext('Timeout waiting for a response from the server.')
                }
                else { /* Assuming disconnected */
                    error.msg = 'disconnected'
                    error.pretty = gettext('Connection with the server was lost.')
                }
            }
            else if (!error.pretty) { /* Unexpected error */
                error.pretty = gettext('Unexpected error while communicating with the server.')
            }

            if (expectedHandle) {
                unexpectEvent(expectedHandle)
            }

            if (handleErrors) {
                logger.error(`ajax error: ${error} (msg="${error.msg}", status=${error.status})`)
            }

            reject(error)

            if (!isListen) {
                syncEndCallbacks.forEach(c => PromiseUtils.asap().then(() => c(handleErrors ? error : null)))
            }
        }

        /* Compose the JWT authorization header */
        let headers = {}
        if (currentUsername && currentPasswordHash) {
            headers['Authorization'] = `Bearer ${makeRequestJWT(currentUsername, currentPasswordHash)}`
        }

        if (!isListen) {
            syncBeginCallbacks.forEach(c => PromiseUtils.asap().then(c))
        }

        AJAX.requestJSON(
            method, path, query, data,
            /* success = */ function (data, headers) {

                resolveWrapper(data)

            },
            /* failure = */ function (data, status, msg, headers) {

                rejectWrapper(data, status, msg)

            },
            headers, timeout
        )
    })
}

function expectEvent(type, params, timeout) {
    let handle = ++expectedEventLastHandle
    expectedEventSpecs[handle] = {
        type: type,
        params: params,
        added: new Date().getTime(),
        timeout: (timeout || DEFAULT_EXPECT_TIMEOUT) * 1000
    }

    return handle
}

function unexpectEvent(handle) {
    delete expectedEventSpecs[handle]
}

function tryMatchExpectedEvent(event) {
    let handle = ObjectUtils.findKey(expectedEventSpecs, function (eventSpec) {
        if (eventSpec.type && eventSpec.type !== event.type) {
            return
        }

        if (eventSpec.params) {
            let mismatched = ObjectUtils.filter(eventSpec.params, function (key, value) {
                if (event.params[key] !== value) {
                    return true
                }
            })

            if (mismatched.length) {
                return
            }
        }

        return true
    })

    if (handle != null) {
        delete expectedEventSpecs[handle]
        return handle
    }

    return null
}

function cleanupExpectedEvents() {
    let now = new Date().getTime()
    expectedEventSpecs = ObjectUtils.filter(expectedEventSpecs, function (handle, eventSpec) {
        let delta = now - eventSpec.added
        if (delta > eventSpec.timeout) {
            logger.warn(`timeout waiting for expected "${eventSpec.type}" event`)
            return false
        }

        return true
    })
}

function handleServerEvent(eventData) {
    let event = new Event(eventData.type, eventData.params)

    let handle = tryMatchExpectedEvent(event)
    if (handle != null) {
        event.expected = true
    }

    if (DEBUG_API_CALLS) {
        let bodyStr = JSON.stringify(event, null, 4).replace(new RegExp('\\n', 'g'), '\n   ')
        logger.debug(`received server event "${event.type}":\n    ${bodyStr}`)
    }
    else {
        logger.debug(`received server event "${event.type}"`)
    }

    callEventListeners(event)
}

/**
 * Generates a fake server event.
 * @memberof QToggle.API
 * @param {String} type event type
 * @param {Object} params event parameters
 */
export function fakeServerEvent(type, params) {
    let event = new Event(type, params)

    let handle = tryMatchExpectedEvent(event)
    if (handle != null) {
        event.expected = true
    }

    if (DEBUG_API_CALLS) {
        let bodyStr = JSON.stringify(event, null, 4).replace(new RegExp('\\n', 'g'), '\n   ')
        logger.debug(`fake server event "${event.type}":\n    ${bodyStr}`)
    }
    else {
        logger.debug(`fake server event "${event.type}"`)
    }

    callEventListeners(event)
}

function callEventListeners(event) {
    eventListeners.forEach(function (listener) {
        listener.callback.apply(listener.thisArg, [event.clone()].concat(listener.args || []))
    })
}

function wait(firstQuick) {
    if (listenWaiting) {
        return setTimeout(wait, 500)
    }

    if (!sessionId) {
        let toHash = String(new Date().getTime() * Math.random())
        let hash = new Crypto.SHA256(toHash).toString().substring(40 - 8)
        sessionId = `qtoggleserverui-${hash}`
    }

    /* Used to detect responses to listening requests that were replaced by new ones */
    let requestListeningTime = listeningTime

    listenWaiting = true
    let timeout = (syncListenError || firstQuick) ? 1 : LISTEN_KEEPALIVE
    let query = {
        session_id: sessionId,
        timeout: timeout
    }

    apiCall({method: 'GET', path: '/listen', query: query, timeout: timeout + SERVER_TIMEOUT}).then(function (result) {

        if (listeningTime !== requestListeningTime) {
            logger.debug('ignoring listen response from older session')
            return
        }

        listenWaiting = false

        asap(wait) /* Schedule the next wait call right away */
        syncListenError = null
        listenErrorCount = 0

        syncListenCallbacks.forEach(c => PromiseUtils.asap().then(c))

        if (result && result.length) {
            result.forEach(handleServerEvent)
        }
        else {
            logger.debug('received server keep-alive')
        }

    }).catch(function (error) {

        let reconnectSeconds = SERVER_RETRY_INTERVAL

        if (listeningTime !== requestListeningTime) {
            logger.debug('ignoring listen response from older session')
            return
        }

        if (ignoreListenErrors) {
            logger.debug(`ignoring listen error: ${error}`)
            syncListenCallbacks.forEach(c => PromiseUtils.asap().then(c))
        }
        else {
            syncListenError = error
            listenErrorCount++

            /* Reconnect fast a few couple of time */
            if (listenErrorCount <= FAST_RECONNECT_LISTEN_ERRORS) {
                reconnectSeconds = 1
            }

            logger.error(`listen failed (reconnecting in ${reconnectSeconds} seconds)`)

            syncListenCallbacks.forEach(c => PromiseUtils.asap().then(() => c(syncListenError, reconnectSeconds)))
        }

        listenWaiting = false

        setTimeout(wait, reconnectSeconds * 1000) /* Schedule the next wait call later */

    })
}


/**
 * Set the API URL prefix.
 * @param {?String} prefix the URL prefix
 */
export function setURLPrefix(prefix) {
    apiURLPrefix = prefix
}


/* Device management */

/**
 * Sets the slave device for the next API call. If no argument or `null` is supplied,
 * the API call will be requested on the master device. Only the immediately following API
 * request will be affected by this setting. Afterwards, the setting will automatically revert to default
 * (i.e. requesting to master).
 * @param {?String} name the slave name
 */
export function setSlave(name) {
    /* If main device name is given, simply clear slave name */
    if (Cache.isMainDevice(name)) {
        name = null
    }

    slaveName = name || null
}

/**
 * GET /device API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getDevice() {
    return apiCall({method: 'GET', path: '/device'})
}

/**
 * PATCH /device API function call.
 * @param {Object} attrs the device attributes to set
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function patchDevice(attrs) {
    let handle
    if (slaveName) {
        /* When renaming a slave, the slave-device-update will not trigger,
         * because the master will actually remove and re-add the slave */
        if (!('name' in attrs)) {
            handle = expectEvent('slave-device-update', {
                name: slaveName
            })
        }
    }
    else {
        handle = expectEvent('device-update')
    }

    return apiCall({method: 'PATCH', path: '/device', data: attrs, expectedHandle: handle})
}

/**
 * POST /reset API function call.
 * @param {Boolean} [factory] set to `true` to reset to factory defaults
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function postReset(factory) {
    let data = {}
    if (factory) {
        data.factory = true
    }
    return apiCall({method: 'POST', path: '/reset', data: data})
}

/**
 * GET /firmware API function call.
 * @param {Boolean} [override] set to `true` to forward request to offline and disabled slaves
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getFirmware(override) {
    let query = {}
    if (override) {
        query.override_offline = true
        query.override_disabled = true
    }

    return apiCall({method: 'GET', path: '/firmware', query: query, handleErrors: false}).then(function (data) {

        if ((data.status === FIRMWARE_STATUS_IDLE || data.status === FIRMWARE_STATUS_ERROR) && ignoreListenErrors) {
            logger.debug('firmware update process ended')
        }

        return data

    })
}

/**
 * PATCH /firmware API function call.
 * @param {?String} version the version to update the device to
 * @param {?String} url the URL of the new firmware
 * @param {Boolean} [override] set to `true` to forward request to offline and disabled slaves
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function patchFirmware(version, url, override) {
    let query = {}
    if (override) {
        query.override_offline = true
        query.override_disabled = true
    }

    let params = {}
    if (version) {
        params.version = version
    }
    if (url) {
        params.url = url
    }

    let forSlave = slaveName != null

    return apiCall({method: 'PATCH', path: '/firmware', query: query, data: params}).then(function (data) {

        if (!forSlave) {
            ignoreListenErrors = true
        }

        return data

    })
}


/* Port management */

/**
 * GET /ports API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getPorts() {
    return apiCall({method: 'GET', path: '/ports'})
}

/**
 * PATCH /ports/{id} API function call.
 * @param {String} id the port identifier
 * @param {Object} attrs the port attributes to set
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function patchPort(id, attrs) {
    let handle = expectEvent('port-update', {
        id: slaveName ? `${slaveName}.${id}` : id
    })

    return apiCall({method: 'PATCH', path: `/ports/${id}`, data: attrs, expectedHandle: handle})
}

/**
 * POST /ports API function call.
 * @param {String} id the port identifier
 * @param {String} type the port type
 * @param {?Number} min a minimum port value
 * @param {?Number} max a maximum port value
 * @param {?Boolean} integer whether the port value must be a integer
 * @param {?Number} step a step for port value validation
 * @param {?Number[]|?String[]} choices valid choices for the port value
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function postPorts(id, type, min, max, integer, step, choices) {
    let handle = expectEvent('port-add', {
        id: slaveName ? `${slaveName}.${id}` : id
    })

    let data = {
        id: id,
        type: type
    }

    if (min != null) {
        data.min = min
    }
    if (max != null) {
        data.max = max
    }
    if (integer != null) {
        data.integer = integer
    }
    if (step != null) {
        data.step = step
    }
    if (choices != null) {
        data.choices = choices
    }

    return apiCall({method: 'POST', path: '/ports', data: data, expectedHandle: handle})
}

/**
 * DELETE /ports/{id} API function call.
 * @param {String} id the port identifier
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function deletePort(id) {
    let handle = expectEvent('port-remove', {
        id: slaveName ? `${slaveName}.${id}` : id
    })

    return apiCall({method: 'DELETE', path: `/ports/${id}`, expectedHandle: handle})
}


/* Port values */

/**
 * GET /ports/{id}/value API function call.
 * @param {String} id the port identifier
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getPortValue(id) {
    return apiCall({method: 'GET', path: `/ports/${id}/value`})
}

/**
 * POST /ports/{id}/value API function call.
 * @param {String} id the port identifier
 * @param {Boolean|Number} value the new port value
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function postPortValue(id, value) {
    let port = Cache.getPort(id)
    let handle = null

    /* Round value to a decent number of decimals */
    if (port && port.type === 'number') {
        value = Math.round(value * ROUND_VALUE_TEMPLATE) / ROUND_VALUE_TEMPLATE
    }

    /* Expect a value-change event only if the currently known value differs from the new one */
    if (!port || port.value == null || port.value !== value) {
        handle = expectEvent('value-change', {
            id: slaveName ? `${slaveName}.${id}` : id,
            value: value
        })
    }

    return apiCall({method: 'POST', path: `/ports/${id}/value`, data: value, expectedHandle: handle})
}

/**
 * POST /ports/{id}/sequence API function call.
 * @param {String} id the port identifier
 * @param {Boolean[]|Number[]} values the list of values in the sequence
 * @param {Number[]} delays the list of delays between values
 * @param {Number} repeat sequence repeat count
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function postPortSequence(id, values, delays, repeat) {
    let data = {values: values, delays: delays, repeat: repeat}

    return apiCall({method: 'POST', path: `/ports/${id}/sequence`, data: data})
}


/* Notifications */

/**
 * Event callback function.
 * @callback QToggle.API.EventCallback
 * @param {QToggle.API.Event} event the event
 */

/**
 * GET /webhooks API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getWebhooks() {
    return apiCall({method: 'GET', path: '/webhooks'})
}

/**
 * PATCH /webhooks API function call.
 * @param {Boolean} enabled whether webhooks are enabled or not
 * @param {String} scheme the URL scheme
 * @param {String} host the host (IP address or hostname) of the client
 * @param {Number} port the TCP port
 * @param {String} path the location for the webhook request
 * @param {Number} timeout the request timeout, in seconds
 * @param {Number} retries the number of retries
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function patchWebhooks(enabled, scheme, host, port, path, timeout, retries) {
    let params = {
        enabled: enabled,
        scheme: scheme,
        host: host,
        port: port,
        path: path,
        timeout: timeout,
        retries: retries
    }

    return apiCall({method: 'PATCH', path: '/webhooks', data: params})
}

/**
 * Convenience function to handle responses to GET /listen API function calls.
 * @param {QToggle.API.EventCallback} eventCallback
 * @param {*} [thisArg] the callback will be called on this object
 */
export function addEventListener(eventCallback, thisArg) {
    eventListeners.push({callback: eventCallback, thisArg: thisArg, args: arguments})
}

/**
 * Removes a previously registered event listener.
 * @param {QToggle.API.EventCallback} eventCallback
 */
export function removeEventListener(eventCallback) {
    let index = eventListeners.findIndex(function (l) {
        return l.callback === eventCallback
    })

    if (index >= 0) {
        eventListeners.splice(index, 1)
    }
}

/**
 * Enables the listening mechanism.
 */
export function startListening() {
    if (listeningTime) {
        throw new AssertionError('Listening mechanism already active')
    }

    logger.debug('starting listening mechanism')

    listeningTime = new Date().getTime()
    wait(/* firstQuick = */ true)
}

/**
 * Disables the listening mechanism.
 */
export function stopListening() {
    logger.debug('stopping listening mechanism')

    listeningTime = null
    listenWaiting = false
}

/**
 * Tells if the listening mechanism is currently enabled.s
 * @returns {Boolean}
 */
export function isListening() {
    return Boolean(listeningTime)
}


/* Reverse API calls */

/**
 * GET /reverse API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getReverse() {
    return apiCall({method: 'GET', path: '/reverse'})
}

/**
 * PATCH /reverse API function call.
 * @param {Boolean} enabled whether the reverse API call mechanism is enabled or not
 * @param {String} scheme the URL scheme
 * @param {String} host the host (IP address or hostname) of the client
 * @param {Number} port the TCP port
 * @param {String} path the location for the reverse request
 * @param {Number} timeout the request timeout, in seconds
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function patchReverse(enabled, scheme, host, port, path, timeout) {
    let params = {
        enabled: enabled,
        scheme: scheme,
        host: host,
        port: port,
        path: path,
        timeout: timeout
    }

    return apiCall({method: 'PATCH', path: '/reverse', data: params})
}


/* Master-slave operation */

/**
 * GET /devices API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getSlaveDevices() {
    return apiCall({method: 'GET', path: '/devices'})
}

/**
 * POST /devices API function call.
 * @param {String} scheme the URL scheme
 * @param {String} host the host (IP address or hostname) of the device
 * @param {Number} port the TCP port
 * @param {String} path the location of the API on the device
 * @param {String} adminPassword the administrator password of the device
 * @param {Number} pollInterval polling interval, in seconds
 * @param {Boolean} listenEnabled whether to enable listening or not
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function postSlaveDevices(scheme, host, port, path, adminPassword, pollInterval, listenEnabled) {
    let params = {
        scheme: scheme,
        host: host,
        port: port,
        path: path,
        admin_password: adminPassword,
        poll_interval: pollInterval,
        listen_enabled: listenEnabled
    }

    let handle = expectEvent('slave-device-add', {
        scheme: scheme,
        host: host,
        port: port,
        path: path
    })

    return apiCall({method: 'POST', path: '/devices', data: params, expectedHandle: handle})
}

/**
 * PATCH /devices/{name} API function call.
 * @param {String} name the device name
 * @param {Boolean} enabled whether the device is enabled or disabled
 * @param {?Number} pollInterval polling interval, in seconds
 * @param {Boolean} listenEnabled whether to enable listening or not
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function patchSlaveDevice(name, enabled, pollInterval, listenEnabled) {
    let params = {
        enabled: enabled,
        poll_interval: pollInterval,
        listen_enabled: listenEnabled
    }

    let handle = expectEvent('slave-device-update', {
        name: name
    })

    return apiCall({method: 'PATCH', path: `/devices/${name}`, data: params, expectedHandle: handle})
}

/**
 * DELETE /devices/{name} API function call.
 * @param {String} name the device name
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function deleteSlaveDevice(name) {
    let handle = expectEvent('slave-device-remove', {
        name: name
    })

    return apiCall({method: 'DELETE', path: `/devices/${name}`, expectedHandle: handle})
}


/* Credentials & rights */

/**
 * GET /access API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getAccess() {
    let promise = apiCall({method: 'GET', path: '/access'})

    return promise.then(function (a) {
        let newAccessLevel = ACCESS_LEVEL_MAPPING[a.level] || ACCESS_LEVEL_NONE

        if (newAccessLevel !== currentAccessLevel) {
            /* Access level changed, notify listeners */

            logger.debug('access level changed from ' +
                         `${ACCESS_LEVEL_MAPPING[currentAccessLevel]} to ${ACCESS_LEVEL_MAPPING[newAccessLevel]}`)

            accessLevelChangeListeners.forEach(function (l) {
                let args = [currentAccessLevel, newAccessLevel].concat(l.args || [])

                asap(function () {
                    l.callback.apply(l.thisArg, args)
                })
            })
        }

        currentAccessLevel = newAccessLevel

        return currentAccessLevel
    })
}

/**
 * Immediately returns the current access level.
 * @returns {?Number} the current access level
 */
export function getCurrentAccessLevel() {
    return currentAccessLevel
}

/**
 * Adds a listener to be called whenever the access level changes.
 * @param {QToggle.API.AccessLevelChangeCallback} callback
 * @param {*} [thisArg] the callback will be called on this object
 */
export function addAccessLevelChangeListener(callback, thisArg) {
    accessLevelChangeListeners.push({callback: callback, thisArg: thisArg, args: arguments})
}

/**
 * Removes a previously registered access level change listener.
 * @param {QToggle.API.AccessLevelChangeCallback} callback
 */
export function removeAccessLevelChangeListener(callback) {
    let index = accessLevelChangeListeners.findIndex(function (l) {
        return l.callback === callback
    })

    if (index >= 0) {
        accessLevelChangeListeners.splice(index, 1)
    }
}

/**
 * Sets the API username.
 * @param {String} username the new username
 */
export function setUsername(username) {
    currentUsername = username
}

/**
 * @returns {String} the current username
 */
export function getUsername() {
    return currentUsername
}

/**
 * Sets the API password.
 * @param {String} password the new password
 */
export function setPassword(password) {
    currentPasswordHash = new Crypto.SHA256(password).toString()
}

/**
 * Directly sets the API password hash.
 * @param {String} hash the new password hash
 */
export function setPasswordHash(hash) {
    currentPasswordHash = hash
}

/**
 * @returns {String} the current password hash
 */
export function getPasswordHash() {
    return currentPasswordHash
}

/**
 * Tells if the given access level is granted.
 * @param {Number} level the desired access level
 * @returns {Boolean}
 */
export function hasAccess(level) {
    return currentAccessLevel >= level
}


/* Dashboard */

/**
 * GET /dashboard/panels API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getDashboardPanels() {
    return apiCall({method: 'GET', path: '/frontend/dashboard/panels'})
}

/**
 * PUT /dashboard/panels API function call.
 * @param {Object} panels the new panels
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function putDashboardPanels(panels) {
    return apiCall({method: 'PUT', path: '/frontend/dashboard/panels', data: panels})
}


/* Prefs */

/**
 * GET /prefs API function call.
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function getPrefs() {
    return apiCall({method: 'GET', path: '/frontend/prefs'})
}

/**
 * PUT /prefs API function call.
 * @param {Object} prefs the new prefs object
 * @returns {Promise} a promise that is resolved when the call succeeds and rejected when it fails;
 *  the resolve argument is the result returned by the API call, while the reject argument is the API call error
 */
export function putPrefs(prefs) {
    return apiCall({method: 'PUT', path: '/frontend/prefs', data: prefs})
}


/* Misc */

/**
 * API request/response indication callback function.
 * @param {QToggle.API.APIError} [error] indicates an error occurred during synchronization
 * @callback QToggle.API.SyncCallback
 */

/**
 * Adds functions to be called each time an API request is initiated and responded. Listen requests are treated
 * separately than regular API requests.
 * The `listenCallback` and `endCallback` functions receive an `error` argument indicating an erroneous result.
 * @param {QToggle.API.SyncCallback} beginCallback the function to be called at the initiation of each API
 *         request
 * @param {QToggle.API.SyncCallback} endCallback the function to be called at the end of each API request
 * @param {QToggle.API.SyncCallback} listenCallback the function to be called whenever a listen request is
 *         responded
 */
export function addSyncCallbacks(beginCallback, endCallback, listenCallback) {
    if (beginCallback) {
        syncBeginCallbacks.push(beginCallback)
    }
    if (endCallback) {
        syncEndCallbacks.push(endCallback)
    }
    if (listenCallback) {
        syncListenCallbacks.push(listenCallback)
    }
}


export function init() {
    setInterval(cleanupExpectedEvents, 1000)
    setURLPrefix(Config.apiURLPrefix)
}

/**
 * @namespace qtoggle.api.base
 */

import Logger from '$qui/lib/logger.module.js'

import {gettext}         from '$qui/base/i18n.js'
import Config            from '$qui/config.js'
import * as AJAX         from '$qui/utils/ajax.js'
import * as Crypto       from '$qui/utils/crypto.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as StringUtils  from '$qui/utils/string.js'

import * as Cache from '$app/cache.js'
import * as Utils from '$app/utils.js'

import * as AuthAPI          from './auth.js'
import * as APIConstants     from './constants.js'
import * as NotificationsAPI from './notifications.js'


const MAX_TIME_SKEW = 300 * 1000 /* Milliseconds */

const logger = Logger.get('qtoggle.api.base')


let sessionId = null
let slaveName = null
let apiURLPrefix = ''
let syncBeginCallbacks = []
let syncEndCallbacks = []
let serverTimestamp = null


/**
 * An API error.
 * @alias qtoggle.api.base.APIError
 */
export class APIError extends Error {

    /**
     * @constructs
     * @param {String} code
     * @param {Number} status
     * @param {String} [pretty]
     * @param {Object} [params]
     */
    constructor({code, status, pretty = '', params = {}}) {
        super(pretty)

        this.code = code
        this.status = status
        this.pretty = pretty
        this.params = params
    }

    /**
     * Create an API error from an HTTP response fields.
     * @param {Object} data response data
     * @param {Number} status response HTTP status
     * @param {String} msg response message
     * @returns {qtoggle.api.base.APIError}
     */
    static fromHTTPResponse(data, status, msg) {
        let errorCode = data['error'] || msg
        let pretty = null
        let params = ObjectUtils.copy(data, /* deep = */ true)
        delete params['error']

        if (data['error']) {
            /* Look through known errors and see if we can find a match */
            APIConstants.KNOWN_ERRORS.some(function (ke) {
                if (ke.code !== data['error']) {
                    return
                }

                if (ke.status && ke.status !== status) {
                    return
                }

                if (!(ke.fields || []).every(f => data[f])) {
                    return
                }

                pretty = StringUtils.formatPercent(ke.pretty, data)

                return true
            })
        }

        if (status === 403) {
            let level = AuthAPI.ACCESS_LEVEL_MAPPING[data['required_level']]
            switch (level) {
                case AuthAPI.ACCESS_LEVEL_ADMIN:
                    pretty = gettext('Administrator access level required.')
                    break

                case AuthAPI.ACCESS_LEVEL_NORMAL:
                    pretty = gettext('Normal access level or higher required.')
                    break

                case AuthAPI.ACCESS_LEVEL_VIEWONLY:
                    pretty = gettext('View-only access level or higher required.')
                    break
            }
        }
        if (status === 500 && data && data.message) {
            /* Internal server error */
            pretty = data.message
        }
        else if (status === 0) {
            if (msg === 'timeout') {
                errorCode = 'timeout'
                pretty = gettext('Timeout waiting for a response from the server.')
            }
            else { /* Assuming disconnected */
                errorCode = 'disconnected'
                pretty = gettext('Connection with the server was lost.')
            }
        }

        if (!pretty) { /* Unexpected error */
            pretty = gettext('Unexpected error while communicating with the server.')
        }

        return new APIError({
            code: errorCode,
            status: status,
            pretty: pretty,
            params: params
        })
    }

    toString() {
        return this.pretty
    }

}

function makeRequestJWT(username, passwordHash) {
    let jwtHeader = {typ: 'JWT', alg: 'HS256'}
    let jwtPayload = {
        usr: username,
        ori: 'consumer',
        iss: 'qToggle'
    }
    let timestamp = new Date().getTime()
    /* If `LISTEN_KEEPALIVE` is set to a larger value, `serverTimestamp` might not be updated as often as we need. */
    let maxTimeSkew = Math.max(MAX_TIME_SKEW, NotificationsAPI.LISTEN_KEEPALIVE)
    if (serverTimestamp == null || Math.abs(serverTimestamp - timestamp) < maxTimeSkew) {
        jwtPayload['iat'] = Math.round(timestamp / 1000)
    }
    let jwtHeaderStr = Crypto.str2b64(JSON.stringify(jwtHeader))
    let jwtPayloadStr = Crypto.str2b64(JSON.stringify(jwtPayload))
    let jwtSigningString = `${jwtHeaderStr}.${jwtPayloadStr}`
    let jwtSignature = new Crypto.HMACSHA256(passwordHash, jwtSigningString).digest()
    let jwtSignatureStr = Crypto.str2b64(Crypto.arr2str(jwtSignature))

    return `${jwtSigningString}.${jwtSignatureStr}`
}


/**
 * Return the unique id of this session.
 * @alias qtoggle.api.base.getSessionId
 * @returns {String}
 */
export function getSessionId() {
    if (!sessionId) {
        let toHash = String(new Date().getTime() * Math.random())
        let hash = new Crypto.SHA256(toHash).toString()
        sessionId = `qtoggleserverui-${hash}`
        sessionId = sessionId.substring(0, 32)
    }

    return sessionId
}

/**
 * Call an API function.
 * @alias qtoggle.api.base.apiCall
 * @param {String} method the method
 * @param {String} path the path (URI)
 * @param {?Object} [query] optional query arguments
 * @param {?Object} [data] optional data (body)
 * @param {?Number} [timeout] timeout, in seconds
 * @param {?Number} [expectedHandle] the handle of the expected event
 * @param {Boolean} [handleErrors] set to `false` to prevent error handling (defaults to `true`)
 * @returns {Promise} a promise that is resolved when the API call succeeds and rejected when it fails; the resolve
 * argument is the result returned by the API call, while the reject argument is the API call error
 */
export function apiCall({
    method,
    path,
    query = null,
    data = null,
    timeout = null,
    expectedHandle = null,
    handleErrors = true
}) {

    let params = {method, path, query, data, timeout, slaveName}

    return new Promise(function (resolve, reject) {
        let apiFuncPath = path
        let slaveForward = false
        if (slaveName) { /* Slave qToggle API call */
            path = `/devices/${slaveName}/forward${path}`
            slaveName = null
            slaveForward = true
        }

        let isListen = apiFuncPath.startsWith('/listen')
        if (apiURLPrefix) {
            path = apiURLPrefix + path
        }

        if (method === 'POST' || method === 'PATCH' || method === 'PUT') {
            if (APIConstants.DEBUG_API_CALLS && data != null) {
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
                syncEndCallbacks.forEach(c => PromiseUtils.asap().then(() => c(/* error = */ null, params)))
            }

            if (APIConstants.DEBUG_API_CALLS && data != null) {
                let bodyStr = JSON.stringify(data, null, 4).replace(new RegExp('\\n', 'g'), '\n   ')
                logger.debug(`response for "${method} ${apiFuncPath}": \n    ${bodyStr}`)
            }
            else {
                logger.debug(`response for "${method} ${apiFuncPath}"`)
            }

            Utils.resolveJSONRefs(data)

            resolve(data)
        }

        function rejectWrapper(data, status, msg) {
            let error = APIError.fromHTTPResponse(data, status, msg)

            if (expectedHandle) {
                NotificationsAPI.unexpectEvent(expectedHandle)
            }

            if (handleErrors) {
                logger.error(`ajax error: ${error} (code="${error.code}", status=${error.status})`)
            }

            reject(error)

            if (!isListen) {
                syncEndCallbacks.forEach(c => PromiseUtils.asap().then(() => c(handleErrors ? error : null, params)))
            }
        }

        let headers = {
            'Session-Id': getSessionId()
        }

        /* Compose the JWT authorization header */
        let username = AuthAPI.getUsername()
        let passwordHash = AuthAPI.getPasswordHash()
        if (username && passwordHash) {
            headers['Authorization'] = `Bearer ${makeRequestJWT(username, passwordHash)}`
        }

        if (!isListen) {
            syncBeginCallbacks.forEach(c => PromiseUtils.asap().then(() => c(params)))
        }

        if (!timeout) {
            timeout = APIConstants.DEFAULT_SERVER_TIMEOUT
        }
        else {
            /* When specifying a timeout, ensure to also use it if forwarding API call to slave */
            if (slaveForward) {
                ObjectUtils.setDefault(query, 'timeout', timeout)
            }
        }

        AJAX.requestJSON(
            method, path, query, data,
            /* success = */ function (data, headers) {

                if (headers['date']) {
                    serverTimestamp = new Date(headers['date']).getTime()
                }
                resolveWrapper(data)

            },
            /* failure = */ function (data, status, msg, headers) {

                if (headers['date']) {
                    serverTimestamp = new Date(headers['date']).getTime()
                }
                rejectWrapper(data, status, msg)

            },
            headers, timeout
        )
    })
}

/**
 * API request indication callback function.
 * @callback qtoggle.api.base.SyncBeginCallback
 * @param {Object} params API call parameters
 */

/**
 * API response indication callback function.
 * @callback qtoggle.api.base.SyncEndCallback
 * @param {?qtoggle.api.base.APIError} [error] indicates an error occurred during request
 * @param {Object} params API call parameters
 */

/**
 * Add a set of functions to be called each time an API request is initiated and responded.
 * @alias qtoggle.api.base.addSyncCallbacks
 * @param {qtoggle.api.base.SyncBeginCallback} [beginCallback] a function to be called at the initiation of each API
 * request
 * @param {qtoggle.api.SyncEndCallback} [endCallback] a function to be called at the end of each API request (when the
 * response is received or an error occurs)
 */
export function addSyncCallbacks(beginCallback = null, endCallback = null) {
    if (beginCallback) {
        syncBeginCallbacks.push(beginCallback)
    }
    if (endCallback) {
        syncEndCallbacks.push(endCallback)
    }
}

/**
 * Set the API URL prefix.
 * @alias qtoggle.api.base.setURLPrefix
 * @param {?String} prefix the URL prefix
 */
export function setURLPrefix(prefix) {
    apiURLPrefix = prefix
}

/**
 * Set the slave device for the next API call. If no argument or `null` is supplied, the API call will be requested on
 * the main device. Only the immediately following API request will be affected by this setting. Afterwards, the setting
 * will automatically revert to default (i.e. requesting to main device).
 * @alias qtoggle.api.base.setSlaveName
 * @param {?String} name the slave name
 */
export function setSlaveName(name) {
    /* If main device name is given, simply clear slave name */
    if (Cache.isMainDevice(name)) {
        name = null
    }

    slaveName = name || null
}

/**
 * Tell the name of the current slave device scheduled for the next API call.
 * @alias qtoggle.api.base.getSlaveName
 * @returns {?String} name the slave name or `null` if no slave is scheduled
 */
export function getSlaveName() {
    return slaveName
}


/**
 * Initialize the base API subsystem.
 * @alias qtoggle.api.base.init
 */
export function init() {
    let apiUrlPrefix
    if (Config.apiURLPrefix != null) {
        apiUrlPrefix = Config.apiURLPrefix
    }
    else {
        apiUrlPrefix = (
            Config.navigationBasePrefix.split('/').slice(0, -1).concat(APIConstants.QTOGGLE_API_PREFIX).join('/')
        )
    }

    setURLPrefix(apiUrlPrefix)
}

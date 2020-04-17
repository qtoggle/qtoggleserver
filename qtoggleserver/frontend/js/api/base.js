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


const logger = Logger.get('qtoggle.api.base')


let slaveName = null
let apiURLPrefix = ''
let syncBeginCallbacks = []
let syncEndCallbacks = []


/**
 * An API error.
 * @alias qtoggle.api.base.APIError
 */
export class APIError extends Error {

    /**
     * @constructs
     * @param {String} messageCode
     * @param {Number} status
     * @param {String} [pretty]
     * @param {Object}params
     */
    constructor({messageCode, status, pretty = '', params = {}}) {
        super(pretty)

        this.messageCode = messageCode
        this.status = status
        this.pretty = pretty
        this.params = params
    }

}

function parseAPIErrorMessageCode(status, message) {
    let parsed = null

    /* Messages starting with "other error: " may encapsulate themselves a known error;
     * we therefore pass the remaining part of the message through the parsing function again */
    let match = message.match(new RegExp('^other error: (.*)$'))
    if (match) {
        parsed = parseAPIErrorMessageCode(status, match[1])
        if (parsed) {
            return parsed
        }
    }

    APIConstants.KNOWN_ERRORS.some(function (e) {
        let match = message.match(e.pattern)
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
 * Create an API error from an HTTP response fields.
 * @alias qtoggle.api.base.makeAPIError
 * @param {Object} data response data
 * @param {Number} status response HTTP status
 * @param {String} msg response message
 * @returns {qtoggle.api.base.APIError}
 */
export function makeAPIError(data, status, msg) {
    let messageCode = data.error || msg
    let prettyMessage = messageCode
    let params = ObjectUtils.copy(data, /* deep = */ true)
    delete params['error']

    let matchedKnownError = null
    if (data.error) {
        matchedKnownError = parseAPIErrorMessageCode(status, data.error)
        if (matchedKnownError) {
            prettyMessage = matchedKnownError.pretty
            if (matchedKnownError.paramNames) {
                matchedKnownError.paramNames.forEach(function (n, i) {
                    params[n] = matchedKnownError.params[i]
                })
            }
        }
    }

    if (status === 403) {
        let level = AuthAPI.ACCESS_LEVEL_MAPPING[data['required_level']]
        switch (level) {
            case AuthAPI.ACCESS_LEVEL_ADMIN:
                prettyMessage = gettext('Administrator access level required.')
                break

            case AuthAPI.ACCESS_LEVEL_NORMAL:
                prettyMessage = gettext('Normal access level required.')
                break

            case AuthAPI.ACCESS_LEVEL_VIEWONLY:
                prettyMessage = gettext('View-only access level required.')
                break
        }
    }
    if (status === 500 && data && data.error) {
        /* Internal server error */
        prettyMessage = data.error
    }
    else if (status === 503 && data && data.error === 'busy') {
        prettyMessage = gettext('The device is busy.')
    }
    else if (status === 0) {
        if (msg === 'timeout') {
            prettyMessage = gettext('Timeout waiting for a response from the server.')
        }
        else { /* Assuming disconnected */
            messageCode = 'disconnected'
            prettyMessage = gettext('Connection with the server was lost.')
        }
    }
    else if (!prettyMessage) { /* Unexpected error */
        prettyMessage = gettext('Unexpected error while communicating with the server.')
    }

    return new APIError({
        messageCode: messageCode,
        status: status,
        pretty: prettyMessage,
        params: params
    })
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
    timeout = APIConstants.DEFAULT_SERVER_TIMEOUT,
    expectedHandle = null,
    handleErrors = true
}) {

    let params = {method, path, query, data, timeout, slaveName}

    return new Promise(function (resolve, reject) {
        let apiFuncPath = path

        if (slaveName) { /* Slave qToggle API call */
            path = `/devices/${slaveName}/forward${path}`
            slaveName = null
        }

        path = APIConstants.QTOGGLE_API_PREFIX + path

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
            let error = makeAPIError(data, status, msg)

            if (expectedHandle) {
                NotificationsAPI.unexpectEvent(expectedHandle)
            }

            if (handleErrors) {
                logger.error(`ajax error: ${error} (messageCode="${error.messageCode}", status=${error.status})`)
            }

            reject(error)

            if (!isListen) {
                syncEndCallbacks.forEach(c => PromiseUtils.asap().then(() => c(handleErrors ? error : null, params)))
            }
        }

        /* Compose the JWT authorization header */
        let headers = {}
        let username = AuthAPI.getUsername()
        let passwordHash = AuthAPI.getPasswordHash()
        if (username && passwordHash) {
            headers['Authorization'] = `Bearer ${makeRequestJWT(username, passwordHash)}`
        }

        if (!isListen) {
            syncBeginCallbacks.forEach(c => PromiseUtils.asap().then(() => c(params)))
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
 * @alias qtoggle.api.base.setSlave
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
 * @alias qtoggle.api.base.getSlave
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
    setURLPrefix(Config.apiURLPrefix)
}

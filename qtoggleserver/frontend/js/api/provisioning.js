/**
 * @namespace qtoggle.api.provisioning
 */

import {gettext}        from '$qui/base/i18n.js'
import * as AJAX        from '$qui/utils/ajax.js'
import * as ArrayUtils  from '$qui/utils/array.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as BaseAPI from './base.js'


const PROVISIONING_CONFIG_URL = 'https://provisioning.qtoggle.io/config'
const PROVISIONING_CONFIG_TIMEOUT = 5 /* Seconds */


/**
 * Backup/restore endpoint details.
 * @alias qtoggle.api.provisioning.BackupEndpoint
 */
export class BackupEndpoint {

    /**
     * @constructs
     * @param {String} path
     * @param {String} displayName
     * @param {Number} order
     * @param {String} [backupMethod]
     * @param {String} [restoreMethod]
     * @param {String[]|Function} [excludeFields]
     */
    constructor({path, displayName, order, backupMethod = 'GET', restoreMethod = 'PUT', excludeFields = []}) {
        this.path = path
        this.displayName = displayName
        this.order = order
        this.backupMethod = backupMethod
        this.restoreMethod = restoreMethod
        this.excludeFields = excludeFields
    }

    /**
     * Return the normalized name of this endpoint (e.g. `"system_configuration"` for a `"/system/configuration"` path).
     * @returns {string}
     */
    getName() {
        return this.path.replace(/[^a-z0-9]/g, '_').replace(/^_/, '').replace(/_$/, '')
    }

    /**
     * Preprocess endpoint-specific data for backup data object.
     * @param {*} endpointData
     */
    prepareBackupData(endpointData) {
        return this._filterEndpointData(endpointData)
    }

    /**
     * Extract and preprocess endpoint-specific data from backup data object.
     * @param {Object} backupData
     * @returns {*}
     */
    prepareRestoreData(backupData) {
        let endpointData = backupData[this.getName()]
        endpointData = this._filterEndpointData(endpointData)

        return endpointData
    }

    _filterEndpointData(endpointData) {
        if (ObjectUtils.isObject(endpointData)) {
            let excludeFields = this.excludeFields
            if (typeof excludeFields !== 'function') {
                excludeFields = (f) => this.excludeFields.includes(f)
            }
            endpointData = ObjectUtils.filter(endpointData, (k, v) => !excludeFields(k))
        }

        return endpointData
    }

}

const DEVICE_BACKUP_ENDPOINT = new BackupEndpoint({
    path: '/device',
    displayName: gettext('Device'),
    order: 10,
    /* Ignore network-related attributes */
    excludeFields: (f) => f.startsWith('wifi_') || f.startsWith('ip_')
})
/* Special endpoint for devices w/o backup support */
const DEVICE_PATCH_BACKUP_ENDPOINT = new BackupEndpoint({
    path: '/device',
    displayName: gettext('Device'),
    restoreMethod: 'PATCH',
    order: 10
})
const PORTS_BACKUP_ENDPOINT = new BackupEndpoint({
    path: '/ports',
    displayName: gettext('Ports'),
    order: 20
})
const WEBHOOKS_BACKUP_ENDPOINT = new BackupEndpoint({
    path: '/webhooks',
    displayName: gettext('Webhooks'),
    order: 30
})
const REVERSE_BACKUP_ENDPOINT = new BackupEndpoint({
    path: '/reverse',
    displayName: gettext('Reverse API Calls'),
    order: 40
})
const SLAVES_BACKUP_ENDPOINT = new BackupEndpoint({
    path: '/devices',
    displayName: gettext('Slave Devices'),
    order: 15
})


/**
 * Return the backup endpoints matching given device flags, including those returned by the GET /backup/endpoints API
 * function call, in the correct order.
 * @alias qtoggle.api.provisioning.getBackupEndpoints
 * @param {String[]} flags
 * @returns {Promise<qtoggle.api.provisioning.BackupEndpoint[]>}
 */
export function getBackupEndpoints(flags) {
    let endpoints = []

    /* Devices w/o backup support can be partially backed up/restored using standard API calls */
    if (!flags.includes('backup')) {
        /* Even if this may not require a real API call, callers will treat it like one, possibly selecting a slave */
        BaseAPI.setSlaveName(null)

        let endpoints = [
            DEVICE_PATCH_BACKUP_ENDPOINT
        ]

        if (flags.includes('webhooks')) {
            endpoints.push(WEBHOOKS_BACKUP_ENDPOINT)
        }
        if (flags.includes('reverse')) {
            endpoints.push(REVERSE_BACKUP_ENDPOINT)
        }

        // TODO: add separate PATCH backup endpoints for all ports

        ArrayUtils.sortKey(endpoints, e => e.order)
        return Promise.resolve(endpoints)
    }

    endpoints = [
        DEVICE_BACKUP_ENDPOINT,
        PORTS_BACKUP_ENDPOINT
    ]

    if (flags.includes('webhooks')) {
        endpoints.push(WEBHOOKS_BACKUP_ENDPOINT)
    }
    if (flags.includes('reverse')) {
        endpoints.push(REVERSE_BACKUP_ENDPOINT)
    }
    if (flags.includes('master')) {
        endpoints.push(SLAVES_BACKUP_ENDPOINT)
    }

    return BaseAPI.apiCall({
        method: 'GET',
        path: '/backup/endpoints'
    }).then(function (data) {
        let extraEndpoints = data.map(e => new BackupEndpoint({
            path: e['path'],
            displayName: e['display_name'],
            order: e['order'],
            restoreMethod: e['restore_method']
        }))

        endpoints.push(...extraEndpoints)

        ArrayUtils.sortKey(endpoints, e => e.order)
        return endpoints
    })
}

/**
 * GET https://provisioning.qtoggle.io/config/available.json file.
 * @alias qtoggle.api.provisioning.getProvisioningConfig
 * @returns {Promise}
 */
export function getProvisioningConfigs() {
    return new Promise(function (resolve, reject) {

        AJAX.requestJSON(
            'GET', `${PROVISIONING_CONFIG_URL}/available.json`, /* query = */ null, /* data = */ null,
            /* success = */ function (configs) {
                let processedConfigs = Object.entries(configs).map(function ([key, value]) {
                    return {
                        name: key,
                        ...value
                    }
                })

                resolve(processedConfigs)
            },
            /* failure = */ function (data, status, msg, headers) {
                reject(BaseAPI.APIError.fromHTTPResponse(data, status, msg))
            },
            /* headers = */ null, /* timeout = */ PROVISIONING_CONFIG_TIMEOUT
        )

    })
}

/**
 * GET https://provisioning.qtoggle.io/config/{config_name}.json file.
 * @alias qtoggle.api.provisioning.getProvisioningConfig
 * @param {String} configName desired configuration name
 * @returns {Promise}
 */
export function getProvisioningConfig(configName) {
    return new Promise(function (resolve, reject) {

        AJAX.requestJSON(
            'GET', `${PROVISIONING_CONFIG_URL}/${configName}.json`, /* query = */ null, /* data = */ null,
            /* success = */ function (configs) {
                resolve(configs)
            },
            /* failure = */ function (data, status, msg, headers) {
                reject(BaseAPI.APIError.fromHTTPResponse(data, status, msg))
            },
            /* headers = */ null, /* timeout = */ PROVISIONING_CONFIG_TIMEOUT
        )

    })
}

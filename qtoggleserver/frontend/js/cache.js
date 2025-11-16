/**
 * @namespace qtoggle.cache
 */

import Logger from '$qui/lib/logger.module.js'

import ConditionVariable from '$qui/base/condition-variable.js'
import {AssertionError}  from '$qui/base/errors.js'
import {gettext}         from '$qui/base/i18n.js'
import Config            from '$qui/config.js'
import * as Toast        from '$qui/messages/toast.js'
import Debouncer         from '$qui/utils/debouncer.js'
import {asap}            from '$qui/utils/misc.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as PromiseUtils from '$qui/utils/promise.js'
import * as Window       from '$qui/window.js'

import * as AuthAPI               from '$app/api/auth.js'
import * as APIConstants          from '$app/api/constants.js'
import * as BaseAPI               from '$app/api/base.js'
import * as DevicesAPI            from '$app/api/devices.js'
import * as PortsAPI              from '$app/api/ports.js'
import * as PrefsAPI              from '$app/api/prefs.js'
import * as ProvisioningAPI       from '$app/api/provisioning.js'
import * as MasterSlaveAPI        from '$app/api/master-slave.js'
import * as NotificationsAPI      from '$app/api/notifications.js'
import {getGlobalProgressMessage} from '$app/common/common.js'


const DEVICE_POLL_INTERVAL = 5 /* Seconds */

/* When actively polling a device, only update some selected attributes */
const DEVICE_POLLED_ATTRIBUTES = [
    'date',
    'uptime',
    'wifi_signal_strength',
    'temperature',
    'cpu_usage',
    'mem_usage',
    'storage_usage',
    'battery_level'
]

const STORAGE_KEY_PREFIX = 'cache'
const STORAGE_SET_DEBOUNCE_DELAY = 5000
const SAVE_PREFS_DEBOUNCE_DELAY = 1000

const logger = Logger.get('qtoggle.cache')


/* Registered slave devices, indexed by name */
let slaveDevices = null

/* Registered ports, indexed by full id */
let allPorts = null

/* Main device attributes */
let mainDevice = null

/* The list of all available provisioning configs */
let provisioningConfigs = null

/* User preferences */
let prefs = null
const savePrefsDebouncer = new Debouncer(() => {
    logger.debug('saving prefs')
    PrefsAPI.putPrefs(prefs)
}, /* delay = */ SAVE_PREFS_DEBOUNCE_DELAY)

/* Indicates that cache needs a reload asap */
let reloadNeeded = false

/* The name of a device to be continuously polled */
let polledDeviceName = null

/* Debouncers for cache setters */
const slaveDevicesSetLocalStorageCacheDebouncer = new Debouncer((slaveDevices) => {
    logger.debug('saving slave devices to cache')
    setLocalStorageCache('slave-devices', slaveDevices)
}, /* delay = */ STORAGE_SET_DEBOUNCE_DELAY)
const allPortsSetLocalStorageCacheDebouncer = new Debouncer((allPorts) => {
    logger.debug('saving all ports to cache')
    setLocalStorageCache('all-ports', allPorts)
}, /* delay = */ STORAGE_SET_DEBOUNCE_DELAY)
const mainDeviceSetLocalStorageCacheDebouncer = new Debouncer((mainDevice) => {
    logger.debug('saving main device to cache')
    setLocalStorageCache('main-device', mainDevice)
}, /* delay = */ STORAGE_SET_DEBOUNCE_DELAY)


/* Some ready condition variables */

/**
 * Wait for the cached device attributes to be loaded.
 * {@link qtoggle.cache.getMainDevice} can be safely called afterwards.
 * @alias qtoggle.cache.whenDeviceCacheReady
 * @type {qui.base.ConditionVariable}
 */
export const whenDeviceCacheReady = new ConditionVariable()

/**
 * Wait for the cached port attributes to be loaded.
 * {@link qtoggle.cache.getPorts} can be safely called afterwards.
 * @alias qtoggle.cache.whenPortsCacheReady
 * @type {qui.base.ConditionVariable}
 */
export const whenPortsCacheReady = new ConditionVariable()

/**
 * Wait for the cached slave device attributes to be loaded.
 * {@link qtoggle.cache.getSlaveDevices} can be safely called afterwards.
 * @alias qtoggle.cache.whenSlaveDevicesCacheReady
 * @type {qui.base.ConditionVariable}
 */
export const whenSlaveDevicesCacheReady = new ConditionVariable()

/**
 * Wait for the cached preferences to be loaded.
 * {@link qtoggle.cache.getPrefs} can be safely called afterwards.
 * @alias qtoggle.cache.whenPrefsCacheReady
 * @type {qui.base.ConditionVariable}
 */
export const whenPrefsCacheReady = new ConditionVariable()

/**
 * Wait for the cached provisioning configurations list to be loaded.
 * {@link qtoggle.cache.getProvisioningConfigs} can be safely called afterwards.
 * @alias qtoggle.cache.whenProvisioningConfigsCacheReady
 * @type {qui.base.ConditionVariable}
 */
export const whenProvisioningConfigsCacheReady = new ConditionVariable()

/**
 * Wait for the initial cached data to be loaded.
 * @alias qtoggle.cache.whenCacheReady
 * @type {qui.base.ConditionVariable}
 */
export let whenCacheReady = new ConditionVariable()

function makeLocalStorageCacheKey(key) {
    return `${STORAGE_KEY_PREFIX}.${key}`
}

/**
 * Retrieve a value from local storage cache.
 * @param {String} key
 * @return the cached value, or `null` if not found in cache
 */
export function getLocalStorageCache(key) {
    let value = window.localStorage.getItem(makeLocalStorageCacheKey(key))
    if (value == null) {
        return null
    }

    return JSON.parse(value)
}

/**
 * Store a value in local storage cache.
 * @param {String} key
 * @param value
 */
export function setLocalStorageCache(key, value) {
    window.localStorage.setItem(makeLocalStorageCacheKey(key), JSON.stringify(value))
}


/**
 * @alias qtoggle.cache.loadDevice
 * @returns {Promise}
 * @param {Boolean} useCache
 */
export function loadDevice(useCache) {
    logger.debug('loading main device')

    let loadPromise = DevicesAPI.getDevice().then(function (attrs) {

        if (mainDevice == null) {
            mainDevice = attrs
            setLocalStorageCache('main-device', attrs)
            whenDeviceCacheReady.fulfill()
        }
        else {
            NotificationsAPI.fakeServerEvent('device-update', attrs)
        }

        logger.debug('loaded main device from server')

    }).catch(function (error) {

        logger.errorStack('loading main device failed', error)
        throw error

    })

    if (useCache && mainDevice == null) {
        let cachedAttrs = getLocalStorageCache('main-device')
        if (cachedAttrs != null) {
            mainDevice = cachedAttrs
            whenDeviceCacheReady.fulfill()
            logger.debug('loaded main device from cache')

            return Promise.resolve()
        }
    }

    return loadPromise
}

/**
 * @alias qtoggle.cache.loadPorts
 * @returns {Promise}
 * @param {Boolean} useCache
 */
export function loadPorts(useCache) {
    logger.debug('loading ports')

    let loadPromise = PortsAPI.getPorts().then(function (ports) {

        if (allPorts == null) {
            allPorts = ObjectUtils.fromEntries(ports.map(p => [p.id, p]))
            setLocalStorageCache('all-ports', allPorts)
            whenPortsCacheReady.fulfill()
        }
        else {
            let newAllPorts = ObjectUtils.fromEntries(ports.map(p => [p.id, p]))
            let removedPorts = Object.values(ObjectUtils.filter(allPorts, (id, port) => !(id in newAllPorts)))
            let addedPorts = Object.values(ObjectUtils.filter(newAllPorts, (id, port) => !(id in allPorts)))

            let updatedPorts = Object.values(ObjectUtils.filter(newAllPorts, function (id, port) {
                let oldPort = allPorts[id]
                if (!oldPort) {
                    return false
                }

                /* Work on copies delete value attributes since we don't want to compare values here */
                let op = ObjectUtils.copy(oldPort)
                let p = ObjectUtils.copy(port)

                delete p.value
                delete op.value

                return !ObjectUtils.deepEquals(op, p)
            }))

            let valueChangedPorts = Object.values(ObjectUtils.filter(newAllPorts, function (id, port) {
                let oldPort = allPorts[id]
                if (!oldPort) {
                    return false
                }

                return oldPort.value !== port.value
            }))

            removedPorts.forEach(function (port) {
                logger.debug(`port ${port.id} has been removed since last server connection`)
                NotificationsAPI.fakeServerEvent('port-remove', {id: port.id})
            })

            addedPorts.forEach(function (port) {
                logger.debug(`port ${port.id} has been added since last server connection`)
                NotificationsAPI.fakeServerEvent('port-add', port)
            })

            updatedPorts.forEach(function (port) {
                logger.debug(`port ${port.id} has been updated since last server connection`)
                NotificationsAPI.fakeServerEvent('port-update', port)
            })

            valueChangedPorts.forEach(function (port) {
                logger.debug(`value of port ${port.id} has changed since last server connection`)
                NotificationsAPI.fakeServerEvent('value-change', port)
            })
        }

        logger.debug(`loaded ${ports.length} ports from server`)

    }).catch(function (error) {

        logger.errorStack('loading ports failed', error)

        throw error

    })

    if (useCache && allPorts == null) {
        let cachedPorts = getLocalStorageCache('all-ports')
        if (cachedPorts != null) {
            allPorts = cachedPorts
            whenPortsCacheReady.fulfill()
            logger.debug(`loaded ${Object.keys(cachedPorts).length} ports from cache`)

            return Promise.resolve()
        }
    }

    return loadPromise
}

/**
 * @alias qtoggle.cache.loadSlaveDevices
 * @returns {Promise}
 * @param {Boolean} useCache
 */
export function loadSlaveDevices(useCache) {
    logger.debug('loading slave devices')

    let loadPromise = MasterSlaveAPI.getSlaveDevices().then(function (devices) {

        if (slaveDevices == null) {
            slaveDevices = ObjectUtils.fromEntries(devices.map(d => [d.name, d]))
            setLocalStorageCache('slave-devices', slaveDevices)
            whenSlaveDevicesCacheReady.fulfill()
        }
        else {
            let newDevices = ObjectUtils.fromEntries(devices.map(d => [d.name, d]))
            let removedDevices = Object.values(ObjectUtils.filter(slaveDevices, (name, d) => !(name in newDevices)))
            let addedDevices = Object.values(ObjectUtils.filter(newDevices, (name, d) => !(name in slaveDevices)))

            let updatedDevices = Object.values(ObjectUtils.filter(newDevices, function (name, device) {
                let oldDevice = slaveDevices[name]
                if (!oldDevice) {
                    return false
                }

                return !ObjectUtils.deepEquals(oldDevice, device)
            }))

            removedDevices.forEach(function (device) {
                logger.debug(`device ${device.name} has been removed since last server connection`)
                NotificationsAPI.fakeServerEvent('slave-device-remove', {name: device.name})
            })

            addedDevices.forEach(function (device) {
                logger.debug(`device ${device.name} has been added since last server connection`)
                NotificationsAPI.fakeServerEvent('slave-device-add', device)
            })

            updatedDevices.forEach(function (device) {
                logger.debug(`device ${device.name} has been updated since last server connection`)
                NotificationsAPI.fakeServerEvent('slave-device-update', device)
            })
        }

        logger.debug(`loaded ${devices.length} slave devices from server`)

    }).catch(function (error) {

        logger.errorStack('loading slave devices failed', error)
        throw error

    })

    if (useCache && slaveDevices == null) {
        let cachedSlaveDevices = getLocalStorageCache('slave-devices')
        if (cachedSlaveDevices != null) {
            slaveDevices = cachedSlaveDevices
            whenSlaveDevicesCacheReady.fulfill()
            logger.debug(`loaded ${Object.keys(cachedSlaveDevices).length} slave devices from cache`)

            return Promise.resolve()
        }
    }

    return loadPromise
}

/**
 * @alias qtoggle.cache.loadPrefs
 * @returns {Promise}
 * @param {Boolean} useCache
 */
export function loadPrefs(useCache) {
    logger.debug('loading prefs')

    let loadPromise = PrefsAPI.getPrefs().then(function (p) {

        if (prefs == null) {
            whenPrefsCacheReady.fulfill()
        }
        prefs = p
        setLocalStorageCache('prefs', prefs)

        logger.debug('loaded prefs from server')

    }).catch(function (error) {

        logger.errorStack('loading prefs failed', error)
        throw error

    })

    if (useCache && prefs == null) {
        let cachedPrefs = getLocalStorageCache('prefs')
        if (cachedPrefs != null) {
            prefs = cachedPrefs
            whenPrefsCacheReady.fulfill()
            logger.debug(`loaded prefs from cache`)

            return Promise.resolve()
        }
    }

    return loadPromise
}

/**
 * @alias qtoggle.cache.loadProvisioningConfigs
 * @returns {Promise}
 * @param {Boolean} useCache
 */
export function loadProvisioningConfigs(useCache) {
    logger.debug('loading provisioning configs')

    let loadPromise = ProvisioningAPI.getProvisioningConfigs().catch(function (error) {

        /* Ignore errors when fetching provisioning configs - they aren't important for the app's well functioning */

        logger.errorStack('loading provisioning configs failed', error)
        return []

    }).then(function (p) {

        if (provisioningConfigs == null) {
            whenProvisioningConfigsCacheReady.fulfill()
        }
        provisioningConfigs = p
        setLocalStorageCache('provisioning-configs', provisioningConfigs)

        logger.debug('loaded provisioning configs from server')

    })

    if (useCache && provisioningConfigs == null) {
        let cachedProvisioningConfigs = getLocalStorageCache('provisioning-configs')
        if (cachedProvisioningConfigs != null) {
            provisioningConfigs = cachedProvisioningConfigs
            whenProvisioningConfigsCacheReady.fulfill()
            logger.debug(`loaded provisioning configs from cache`)

            return Promise.resolve()
        }
    }

    return loadPromise
}

/**
 * @alias qtoggle.cache.load
 * @param {Number} accessLevel
 * @param {Boolean} showModalProgress
 * @param {Boolean} useCache
 * @returns {Promise}
 */
export function load(accessLevel, showModalProgress, useCache) {
    let loadPromises = []
    let progressMessage = null
    if (showModalProgress) {
        progressMessage = getGlobalProgressMessage().show()
    }

    if (accessLevel >= AuthAPI.ACCESS_LEVEL_ADMIN) {
        loadPromises.push(loadDevice(useCache))
    }

    if (accessLevel >= AuthAPI.ACCESS_LEVEL_VIEWONLY) {
        loadPromises.push(loadPorts(useCache))
    }

    if (accessLevel >= AuthAPI.ACCESS_LEVEL_ADMIN && Config.slavesEnabled) {
        loadPromises.push(loadSlaveDevices(useCache))
    }

    if (accessLevel >= AuthAPI.ACCESS_LEVEL_VIEWONLY) {
        loadPromises.push(loadPrefs(useCache))
    }

    if (accessLevel >= AuthAPI.ACCESS_LEVEL_ADMIN) {
        loadPromises.push(loadProvisioningConfigs(useCache))
    }

    let loadPromise = Promise.all(loadPromises)
    if (progressMessage) {
        progressMessage.setMessage(gettext('Loading data...'))
    }

    loadPromise.catch(function (error) {

        /* Handle any error that might have occurred during loading and retry indefinitely */

        let errorMsg = error.toString()
        let promise = PromiseUtils.later(APIConstants.SERVER_RETRY_INTERVAL * 1000)

        if (progressMessage) {
            progressMessage.setMessage(gettext('Reconnecting...'))
        }
        else {
            if (NotificationsAPI.isConnected()) {
                Toast.error(errorMsg)
            }
        }

        return promise.then(function () {
            return load(accessLevel, showModalProgress, useCache)
        })

    })

    loadPromise = loadPromise.then(function () {
        if (!whenCacheReady.isFulfilled()) {
            logger.debug('cached data ready')
            whenCacheReady.fulfill()
        }

        if (progressMessage) {
            progressMessage.hide()
        }
    })

    return loadPromise
}

/**
 * Update cache from event.
 * @alias qtoggle.cache.updateFromEvent
 * @param {qtoggle.api.notifications.Event} event
 */
export function updateFromEvent(event) {
    let device, port

    if (!whenCacheReady.isFulfilled()) {
        /* Ignore events while cache not ready */
        return
    }

    switch (event.type) {
        case 'slave-device-update': {
            if (event.params.name in slaveDevices) {
                slaveDevices[event.params.name] = ObjectUtils.copy(event.params, /* deep = */ true)
                slaveDevicesSetLocalStorageCacheDebouncer.call(slaveDevices)
            }
            else {
                logger.warn(`received slave-device-update event for unknown device "${event.params.name}"`)
            }

            break
        }

        case 'slave-device-polling-update': {
            if (event.params.name in slaveDevices) {
                Object.assign(slaveDevices[event.params.name].attrs, event.params.attrs)
                slaveDevicesSetLocalStorageCacheDebouncer.call(slaveDevices)
            }
            else {
                logger.warn(`received slave-device-polling-update event for unknown device "${event.params.name}"`)
            }

            break
        }

        case 'slave-device-add': {
            if (event.params.name in slaveDevices) {
                logger.debug(`received slave-device-add event for already existing device "${event.params.name}"`)
            }

            slaveDevices[event.params.name] = ObjectUtils.copy(event.params, /* deep = */ true)
            slaveDevicesSetLocalStorageCacheDebouncer.call(slaveDevices)

            break
        }

        case 'slave-device-remove': {
            device = slaveDevices[event.params.name]
            if (device) {
                delete slaveDevices[event.params.name]
                slaveDevicesSetLocalStorageCacheDebouncer.call(slaveDevices)
            }
            else {
                logger.warn(`received slave-device-remove event for unknown device "${event.params.name}"`)
            }

            if (polledDeviceName === event.params.name) {
                polledDeviceName = null
            }

            break
        }

        case 'value-change': {
            port = allPorts[event.params.id]
            if (port) {
                port.value = event.params.value
                if (port.value != null) {
                    port.last_sync = Math.round(new Date().getTime() / 1000)
                }
                allPortsSetLocalStorageCacheDebouncer.call(allPorts)
            }
            else {
                logger.warn(`received value-change event for unknown port "${event.params.id}"`)
            }

            break
        }

        case 'port-update': {
            if (!(event.params.id in allPorts)) {
                logger.warn(`received port-update event for unknown port "${event.params.id}"`)
            }

            allPorts[event.params.id] = ObjectUtils.copy(event.params, /* deep = */ true)
            allPortsSetLocalStorageCacheDebouncer.call(allPorts)

            break
        }

        case 'port-add': {
            if (event.params.id in allPorts) {
                logger.debug(`received port-add-event for already existing port "${event.params.id}"`)
            }

            allPorts[event.params.id] = ObjectUtils.copy(event.params, /* deep = */ true)
            allPortsSetLocalStorageCacheDebouncer.call(allPorts)

            break
        }

        case 'port-remove': {
            port = allPorts[event.params.id]
            if (port) {
                delete allPorts[event.params.id]
                allPortsSetLocalStorageCacheDebouncer.call(allPorts)
            }
            else {
                logger.warn(`received port-remove event for unknown port "${event.params.id}"`)
            }

            break
        }

        case 'device-update': {
            mainDevice = event.params
            mainDeviceSetLocalStorageCacheDebouncer.call(mainDevice)

            break
        }

        case 'full-update': {
            reload(/* now = */ true)

            break
        }

        case 'device-polling-update': {
            Object.assign(mainDevice, event.params)
            mainDeviceSetLocalStorageCacheDebouncer.call(mainDevice)

            break
        }

    }
}

/**
 * Return the cached main device attributes.
 * @alias qtoggle.cache.getMainDevice
 * @returns {Object}
 */
export function getMainDevice() {
    if (!whenDeviceCacheReady.isFulfilled()) {
        throw new AssertionError('Main device accessed before cache ready')
    }

    return ObjectUtils.copy(mainDevice, /* deep = */ true)
}

/**
 * Return the cached ports.
 * @alias qtoggle.cache.getPorts
 * @param {Boolean} [asList] whether to return ports as a list or as a dictionary
 * @returns {Object|Object[]}
 */
export function getPorts(asList = false) {
    if (!whenPortsCacheReady.isFulfilled()) {
        throw new AssertionError('Ports accessed before cache ready')
    }

    if (asList) {
        return Object.values(allPorts)
    }
    else {
        return ObjectUtils.copy(allPorts)
    }
}

/**
 * Look up a cached port by id.
 * @alias qtoggle.cache.getPort
 * @param {String} id
 * @returns {?Object}
 */
export function getPort(id) {
    if (!whenPortsCacheReady.isFulfilled()) {
        throw new AssertionError('Ports accessed before cache ready')
    }

    return allPorts[id] || null
}

/**
 * Return the cached slave devices.
 * @alias qtoggle.cache.getSlaveDevices
 * @param {Boolean} [asList] whether to return devices as a list or as a dictionary
 * @returns {Object|Object[]}
 */
export function getSlaveDevices(asList = false) {
    if (!whenSlaveDevicesCacheReady.isFulfilled()) {
        throw new AssertionError('Slave devices accessed before cache ready')
    }

    if (asList) {
        return Object.values(slaveDevices)
    }
    else {
        return ObjectUtils.copy(slaveDevices)
    }
}

/**
 * Look up a cached slave device by name.
 * @alias qtoggle.cache.getSlaveDevice
 * @param {String} name
 * @returns {?Object}
 */
export function getSlaveDevice(name) {
    if (!whenSlaveDevicesCacheReady.isFulfilled()) {
        throw new AssertionError('Devices accessed before cache ready')
    }

    return slaveDevices[name] || null
}

/**
 * Return the slave device owning the port with a given id.
 * @alias qtoggle.cache.findPortSlaveDevice
 * @param {String} portId
 * @returns {?Object} the slave device, if found
 */
export function findPortSlaveDevice(portId) {
    if (!Config.slavesEnabled || slaveDevices == null) {
        return null
    }

    return ObjectUtils.findValue(slaveDevices, function (deviceName) {
        return portId.startsWith(`${deviceName}.`)
    })
}

/**
 * Return the navigable path to a port with given id.
 * @alias qtoggle.cache.getPortPath
 * @param {String} portId
 * @param {String} [deviceName]
 * @returns {String}
 */
export function getPortPath(portId, deviceName = null) {
    let path = '/ports'

    if (!Config.slavesEnabled || slaveDevices == null) {
        path += `/~${portId}`
    }
    else {
        if (!deviceName) {
            let device = findPortSlaveDevice(portId)
            if (device) {
                deviceName = device.name
            }
            else {
                deviceName = ''
            }
        }

        if (deviceName) {
            let remoteId = portId
            if (remoteId.startsWith(`${deviceName}.`)) {
                remoteId = remoteId.substring(deviceName.length + 1)
            }
            path += `/~${deviceName}/~${remoteId}`
        }
        else {
            path += `/~${mainDevice.name}/~${portId}`
        }
    }

    return path
}

/**
 * Tell if a given name is the name of the main device.
 * @alias qtoggle.cache.isMainDevice
 * @param {String} name
 */
export function isMainDevice(name) {
    return name === mainDevice.name
}

/**
 * Return user's preferences at given path. If no path is supplied, the root preferences object is returned.
 * @alias qtoggle.cache.getPrefs
 * @param {String} [path]
 * @param {*} [def] default value in case of missing prefs at given value
 */
export function getPrefs(path = null, def = null) {
    if (!whenPrefsCacheReady.isFulfilled()) {
        throw new AssertionError('Preferences accessed before cache ready')
    }

    if (!path) {
        return prefs
    }

    function getPrefsRec(prefsObj, pathArray) {
        if (!pathArray.length) {
            return prefsObj
        }

        let next = prefsObj[pathArray[0]]
        if (next === undefined) {
            return def
        }

        return getPrefsRec(next, pathArray.slice(1))
    }

    return getPrefsRec(prefs, path.split('.'))
}

/**
 * Update user's preferences at the given path.
 * @alias qtoggle.cache.setPrefs
 * @param {String} path
 * @param {*} value
 */
export function setPrefs(path, value) {
    if (!whenPrefsCacheReady.isFulfilled()) {
        throw new AssertionError('Preferences accessed before cache ready')
    }

    function setPrefsRec(prefsObj, pathArray) {
        if (pathArray.length === 1) {
            prefsObj[pathArray[0]] = value
            return
        }

        let next = prefsObj[pathArray[0]]
        if (!ObjectUtils.isObject(next)) {
            next = prefsObj[pathArray[0]] = {}
        }

        setPrefsRec(next, pathArray.slice(1))
    }

    if (!path) {
        prefs = value
    }
    else {
        setPrefsRec(prefs, path.split('.'))
    }

    savePrefsDebouncer.call()
    setLocalStorageCache('prefs', prefs)
}

/**
 * Return the cached main device attributes.
 * @alias qtoggle.cache.getProvisioningConfigs
 * @returns {Object}
 */
export function getProvisioningConfigs() {
    if (!whenProvisioningConfigsCacheReady.isFulfilled()) {
        throw new AssertionError('Provisioning configs accessed before cache ready')
    }

    return provisioningConfigs
}

/**
 * Set the *reload needed* flag, determining a {@link qtoggle.cache.load} upon next listen response.
 * @alias qtoggle.cache.reload
 * @param {Boolean} [now] set to `true` to reload asap instead of waiting till the next listen request
 */
export function reload(now = false) {
    logger.debug('cache will be reloaded asap')
    reloadNeeded = true

    if (now) {
        if (NotificationsAPI.isListening()) {
            NotificationsAPI.stopListening()
        }
        NotificationsAPI.startListening()
    }
}

/**
 * Return the name of the polled device.
 * @alias qtoggle.cache.getPolledDeviceName
 * @returns {?String}
 */
export function getPolledDeviceName() {
    return polledDeviceName
}

/**
 * Set the name of the polled device. Passing `null` disables polling.
 * @alias qtoggle.cache.setPolledDeviceName
 * @param {?String} [deviceName]
 */
export function setPolledDeviceName(deviceName) {
    if (deviceName == null) {
        logger.debug('disabling device polling')
    }
    else {
        logger.debug(`setting polled device name to "${deviceName}"`)
    }

    polledDeviceName = deviceName
}

function pollDevice() {
    /* Choose between polling main device or a slave device */
    let device = null
    if (polledDeviceName) {
        logger.debug(`polling device "${polledDeviceName}"`)
        device = slaveDevices[polledDeviceName]
        if (!device) {
            logger.debug('skipping polling for unknown device')
            return
        }

        if (!device.enabled) {
            logger.debug('skipping polling for disabled device')
            return
        }

        BaseAPI.setSlaveName(polledDeviceName)
    }
    else {
        logger.debug('polling main device')
    }

    DevicesAPI.getDevice().then(function (attrs) {

        asap(function () {
            if (device && polledDeviceName === device.name) {
                if (!ObjectUtils.deepEquals(device.attrs, attrs)) {
                    let partialDevice = {name: device.name, attrs: {}}
                    DEVICE_POLLED_ATTRIBUTES.forEach(function (name) {
                        if (name in attrs) {
                            partialDevice.attrs[name] = attrs[name]
                        }
                    })
                    NotificationsAPI.fakeServerEvent('slave-device-polling-update', partialDevice)
                }
            }
            else if (polledDeviceName === '') {
                if (!ObjectUtils.deepEquals(mainDevice, attrs)) {
                    let partialAttrs = {}
                    DEVICE_POLLED_ATTRIBUTES.forEach(function (name) {
                        if (name in attrs) {
                            partialAttrs[name] = attrs[name]
                        }
                    })
                    NotificationsAPI.fakeServerEvent('device-polling-update', partialAttrs)
                }
            }
        })

    }).catch(function (e) {

        if (polledDeviceName == null) {
            logger.debug('ignoring polling error after polling disabled')
            return
        }
        if ((e instanceof BaseAPI.APIError) && (e.code === 'no such device')) {
            logger.debug('ignoring error while polling removed device')
            return
        }

        logger.errorStack('polling failed', e)

    })
}

/**
 * Initialize the cache subsystem.
 * @alias qtoggle.cache.init
 */
export function init() {
    /* Reload cache upon next successful listen callback, if needed */
    NotificationsAPI.addSyncListenCallback(function (error) {

        if (!error) { /* Successful listen response */
            if (reloadNeeded) {
                reloadNeeded = false
                load(AuthAPI.getCurrentAccessLevel(), /* showModalProgress = */ false, /* useCache = */ false)
            }
        }

    })

    /* Start a polling timer */
    setInterval(function () {

        /* Don't poll unless cache is ready */
        if (!whenCacheReady.isFulfilled()) {
            return
        }

        /* Don't poll unless window currently active */
        if (!Window.isActive()) {
            return
        }

        /* Don't poll if polling device disabled */
        if (polledDeviceName == null) {
            return
        }

        pollDevice()

    }, DEVICE_POLL_INTERVAL * 1000)
}

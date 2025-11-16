/**
 * @namespace qtoggle.events
 */

import Logger from '$qui/lib/logger.module.js'

import {gettext}        from '$qui/base/i18n.js'
import * as Status      from '$qui/main-ui/status.js'
import * as Messages    from '$qui/messages/messages.js'
import * as Toast       from '$qui/messages/toast.js'
import * as ArrayUtils  from '$qui/utils/array.js'
import {asap}           from '$qui/utils/misc.js'
import * as ObjectUtils from '$qui/utils/object.js'
import * as StringUtils from '$qui/utils/string.js'

import * as BaseAPI               from '$app/api/base.js'
import * as NotificationsAPI      from '$app/api/notifications.js'
import * as Cache                 from '$app/cache.js'
import {getGlobalProgressMessage} from '$app/common/common.js'
import * as Sections              from '$app/sections.js'


/* Attributes that are ignored when showing notification messages */
const IGNORE_CHANGE_PORT_ATTRS = ['last_sync', 'value']
const IGNORE_CHANGE_DEVICE_ATTRS = ['uptime', 'date', 'battery_level']
const IGNORE_CHANGE_SLAVE_ATTRS = ['last_sync', 'attrs']

const logger = Logger.get('qtoggle.events')

/* Used to gather and process all events received with a single request */
let eventsBulk = []
let eventsBulkTimeoutHandle = null

/* Active sync requests status */
let syncCount = 0
let syncError = null
let syncListenError = null

/* Progress message for recent listen error */
let listenErrorProgressMessage = null


/* This function is given all events received with a single request, so that it has a general overview on all generated
 * events */
function processEventsBulk() {
    /* Do a first round to display some notification messages */
    showMessageFromEvents(eventsBulk)

    /* Do a second round to:
     *  * update ports/devices cache and other cached info
     *  * notify section listeners */
    let allSections = Sections.all()
    eventsBulk.forEach(function (event) {
        try {
            Cache.updateFromEvent(event)
        }
        catch (e) {
            logger.errorStack('updating cache from event failed', e)
        }

        allSections.forEach(function (section) {
            try {
                section.onServerEvent(event)
            }
            catch (e) {
                logger.errorStack(`'section "${section.getId()}" server event handling failed`, e)
            }
        })
    })

    /* Reset bulk events processing mechanism */
    eventsBulkTimeoutHandle = 0
    eventsBulk = []
}

function showMessageFromEvents(events) {
    let message = null
    let messageType = null

    let messagesEvents = events.filter(function (e) {
        return !((e.type === 'port-update' ||
                  e.type === 'device-update' ||
                  e.type === 'slave-device-update') && e.expected)
    })

    messagesEvents.forEach(function (event) {
        let device, port
        let deviceLabel, portLabel
        let groupedEvents

        switch (event.type) {
            case 'slave-device-update': {
                device = Cache.getSlaveDevice(event.params.name)
                if (!device) {
                    break
                }

                /* Do not show notifications unless an attribute that is not ignored has been changed */
                let slaveChanged = Object.keys(ObjectUtils.filter(device, function (name, value) {
                    return (!ObjectUtils.deepEquals(event.params[name], value) &&
                            !IGNORE_CHANGE_SLAVE_ATTRS.includes(name))
                })).length > 0

                let slaveAttrsChanged = Object.keys(ObjectUtils.filter(device.attrs, function (name, value) {
                    return (!ObjectUtils.deepEquals(event.params.attrs[name], value) &&
                            !IGNORE_CHANGE_DEVICE_ATTRS.includes(name))
                })).length > 0

                if (!slaveChanged && !slaveAttrsChanged) {
                    break
                }

                deviceLabel = Messages.wrapLabel(event.params.attrs.display_name || event.params.name)

                if (!device.enabled && event.params.enabled) { /* Enabled */
                    message = StringUtils.formatPercent(
                        gettext('Device %(device)s has been enabled.'),
                        {device: deviceLabel}
                    )
                    messageType = 'info'
                }
                else if (device.enabled && !event.params.enabled) { /* Disabled */
                    message = StringUtils.formatPercent(
                        gettext('Device %(device)s has been disabled.'),
                        {device: deviceLabel}
                    )
                    messageType = 'info'
                }
                else if (!device.online && event.params.online) { /* Came online */
                    message = StringUtils.formatPercent(
                        gettext('Device %(device)s is now online.'),
                        {device: deviceLabel}
                    )
                    messageType = 'info'
                }
                else if (device.online && !event.params.online) { /* Went offline */
                    message = StringUtils.formatPercent(
                        gettext('Device %(device)s is offline.'),
                        {device: deviceLabel}
                    )
                    messageType = 'warning'
                }

                break
            }

            case 'slave-device-add': {
                deviceLabel = Messages.wrapLabel(event.params.attrs.display_name || event.params.name)
                message = StringUtils.formatPercent(
                    gettext('Device %(device)s has been added.'),
                    {device: deviceLabel}
                )
                messageType = 'info'

                break
            }

            case 'slave-device-remove': {
                device = Cache.getSlaveDevice(event.params.name)
                if (!device) {
                    break
                }

                deviceLabel = Messages.wrapLabel(device.attrs.display_name || device.name)
                message = StringUtils.formatPercent(
                    gettext('Device %(device)s has been removed.'),
                    {device: deviceLabel}
                )
                messageType = 'info'

                break
            }

            case 'value-change': {
                break
            }

            case 'port-update': {
                port = Cache.getPort(event.params.id)
                if (!port) {
                    break
                }

                /* Do not show notifications unless an attribute that is not ignored has been changed */
                let portAttrsChanged = Object.keys(ObjectUtils.filter(port, function (name, value) {
                    return (!ObjectUtils.deepEquals(event.params[name], value) &&
                            !IGNORE_CHANGE_PORT_ATTRS.includes(name))
                })).length > 0

                if (!portAttrsChanged) {
                    break
                }

                portLabel = Messages.wrapLabel(event.params.display_name || event.params.id)
                device = Cache.findPortSlaveDevice(port.id)

                /* Do not show notifications for ports belonging to permanently offline devices,
                 * since they tend to generate many events via webhooks */
                if (device && (!device.listen_enabled && !device.poll_enabled)) {
                    break
                }

                if (!port.enabled && event.params.enabled) { /* Enabled */
                    message = StringUtils.formatPercent(
                        gettext('Port %(port)s has been enabled.'),
                        {port: portLabel}
                    )
                    messageType = 'info'
                }
                else if (port.enabled && !event.params.enabled) { /* Disabled */
                    message = StringUtils.formatPercent(
                        gettext('Port %(port)s has been disabled.'),
                        {port: portLabel}
                    )
                    messageType = 'info'
                }
                else if (!port.online && event.params.online) { /* Came online */
                    /* If more than one port of a device came online,
                     * avoid showing a message for each of its ports */
                    groupedEvents = messagesEvents.filter(function (e) {
                        if (e.type !== 'port-update') {
                            return false
                        }

                        let p = Cache.getPort(e.params.id)
                        if (!p) {
                            return false
                        }

                        let d = Cache.findPortSlaveDevice(p.id)
                        if (d !== device) {
                            return
                        }

                        return !p.online && e.params.online
                    })

                    /* Eliminate port duplicates */
                    groupedEvents = ArrayUtils.distinct(groupedEvents, function (e1, e2) {
                        return e1.params.id === e2.params.id
                    })

                    messageType = 'info'
                    if (groupedEvents.length === 1) {
                        message = StringUtils.formatPercent(
                            gettext('Port %(port)s is now online.'),
                            {port: portLabel}
                        )
                    }
                    else {
                        message = StringUtils.formatPercent(
                            gettext('%(count)d ports are now online.'),
                            {count: groupedEvents.length}
                        )
                    }
                }
                else if (port.online && !event.params.online) { /* Went offline */
                    /* If more than one port of a device went offline,
                     * avoid showing a message for each of its ports */
                    groupedEvents = messagesEvents.filter(function (e) {
                        if (e.type !== 'port-update') {
                            return false
                        }

                        let p = Cache.getPort(e.params.id)
                        if (!p) {
                            return false
                        }

                        let d = Cache.findPortSlaveDevice(p.id)
                        if (d !== device) {
                            return
                        }

                        return p.online && !e.params.online
                    })

                    /* Eliminate port duplicates */
                    groupedEvents = ArrayUtils.distinct(groupedEvents, function (e1, e2) {
                        return e1.params.id === e2.params.id
                    })

                    messageType = 'warning'
                    if (groupedEvents.length === 1) {
                        message = StringUtils.formatPercent(
                            gettext('Port %(port)s is offline.'),
                            {port: portLabel}
                        )
                    }
                    else {
                        message = StringUtils.formatPercent(
                            gettext('%(count)d ports are offline.'),
                            {count: groupedEvents.length}
                        )
                    }
                }

                break
            }

            case 'port-add': {
                portLabel = Messages.wrapLabel(event.params.display_name || event.params.id)
                device = Cache.findPortSlaveDevice(event.params.id)

                /* If more than one port of a device have been added,
                 * avoid showing a message for each of the ports */
                groupedEvents = messagesEvents.filter(function (e) {
                    if (e.type !== 'port-add') {
                        return false
                    }

                    let d = Cache.findPortSlaveDevice(e.params.id)
                    if (d !== device) {
                        return
                    }

                    return true
                })

                /* Eliminate port duplicates */
                groupedEvents = ArrayUtils.distinct(groupedEvents, function (e1, e2) {
                    return e1.params.id === e2.params.id
                })

                messageType = 'info'
                if (groupedEvents.length === 1) {
                    message = StringUtils.formatPercent(
                        gettext('Port %(port)s has been added.'),
                        {port: portLabel}
                    )
                }
                else {
                    message = StringUtils.formatPercent(
                        gettext('%(count)d ports have been added.'),
                        {count: groupedEvents.length}
                    )
                }

                break
            }

            case 'port-remove': {
                port = Cache.getPort(event.params.id)
                if (!port) {
                    break
                }

                portLabel = Messages.wrapLabel(port.display_name || port.id)
                device = Cache.findPortSlaveDevice(port.id)

                /* If more than one port of a device have been removed,
                 * avoid showing a message for each of the ports */
                groupedEvents = messagesEvents.filter(function (e) {
                    if (e.type !== 'port-remove') {
                        return false
                    }

                    let d = Cache.findPortSlaveDevice(e.params.id)
                    if (d !== device) {
                        return
                    }

                    return true
                })

                /* Eliminate port duplicates */
                groupedEvents = ArrayUtils.distinct(groupedEvents, function (e1, e2) {
                    return e1.params.id === e2.params.id
                })

                messageType = 'info'
                if (groupedEvents.length === 1) {
                    message = StringUtils.formatPercent(
                        gettext('Port %(port)s has been removed.'),
                        {port: portLabel}
                    )
                }
                else {
                    message = StringUtils.formatPercent(
                        gettext('%(count)d ports have been removed.'),
                        {count: groupedEvents.length}
                    )
                }

                break
            }
        }
    })

    /* Actually show the message */
    if (message) {
        Toast.show({message: message, type: messageType})
    }
}

function updateStatusIcon() {
    let status
    let message

    if (syncListenError) {
        status = Status.STATUS_SYNC
        message = syncListenError.message
    }
    else if (syncError) {
        status = Status.STATUS_ERROR
        message = syncError.message
    }
    else if (syncCount > 0) {
        status = Status.STATUS_SYNC
    }
    else {
        status = Status.STATUS_OK
    }

    Status.set(status, message)
}


/**
 * Initialize the events subsystem.
 * @alias qtoggle.events.init
 */
export function init() {
    NotificationsAPI.addEventListener(function (event) {
        eventsBulk.push(event)
        if (eventsBulkTimeoutHandle) {
            clearTimeout(eventsBulkTimeoutHandle)
        }

        /* Ignore any event that is received before cache is ready */
        if (!Cache.whenCacheReady.isFulfilled()) {
            logger.debug('ignoring event before cache ready')
            return
        }

        eventsBulkTimeoutHandle = asap(processEventsBulk)
    })

    BaseAPI.addSyncCallbacks(
        /* beginCallback = */ function () {

            /* Reset sync error when all pending API requests have finished and are successful */
            if (syncCount === 0) {
                syncError = null
            }

            syncCount++
            updateStatusIcon()

        },
        /* endCallback = */ function (error) {

            syncCount--
            if (error) {
                syncError = error
            }

            updateStatusIcon()

        }
    )

    NotificationsAPI.addSyncListenCallback(function (error, reconnectSeconds) {
        if (error) {
            if (!syncListenError) {
                logger.error('disconnected from server')

                Sections.all().forEach(function (section) {
                    asap(() => section.onMainDeviceDisconnect(error))
                })
            }

            syncListenError = error

            if (reconnectSeconds > 1) {
                if (!listenErrorProgressMessage) {
                    listenErrorProgressMessage = getGlobalProgressMessage().show()
                    listenErrorProgressMessage.setMessage(gettext('Reconnecting...'))
                }
            }
        }
        else { /* Successful listen response */
            if (syncListenError) {
                syncListenError = null

                Sections.all().forEach(function (section) {
                    asap(() => section.onMainDeviceReconnect())
                })

                if (listenErrorProgressMessage) {
                    listenErrorProgressMessage.hide()
                    listenErrorProgressMessage = null
                }

                logger.info('reconnected to server')

                Cache.reload()
            }
        }

        updateStatusIcon()

    })
}

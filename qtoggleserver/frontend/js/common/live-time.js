/**
 * @namespace qtoggle.common.livetime
 */

import {gettext}        from '$qui/base/i18n.js'
import * as DateUtils   from '$qui/utils/date.js'
import * as StringUtils from '$qui/utils/string.js'

import * as BaseAPI from '$app/api/base.js'


const REFRESH_INTERVAL = 10 * 1000 /* Milliseconds */
const TICK_INTERVAL = 1000 /* Milliseconds */


function formatAge(seconds) {
    if (seconds < 60) {
        return `${seconds} ${gettext('s')}`
    }
    if (seconds < 3600) {
        return `${Math.floor(seconds / 60)} ${gettext('min')}`
    }
    if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)} ${gettext('h')}`
    }

    return `${Math.floor(seconds / 86400)} ${gettext('days')}`
}


/**
 * Format a time given in seconds since Epoch, followed by how long ago it was. `0` or `null` means never.
 * @alias qtoggle.common.livetime.formatTimeAgo
 * @param {?Number} timestamp
 * @returns {String}
 */
export function formatTimeAgo(timestamp) {
    if (!timestamp) {
        return `(${gettext('never')})`
    }

    let time = DateUtils.formatPercent(new Date(timestamp * 1000), '%Y-%m-%d %H:%M:%S')
    let age = Math.max(0, Math.round(BaseAPI.getServerTime() / 1000 - timestamp))

    return `${time} (${StringUtils.formatPercent(gettext('%(age)s ago'), {age: formatAge(age)})})`
}


/**
 * Keeps a time on display while a page is open: fetches it again every few seconds and ticks its age every second.
 * @alias qtoggle.common.livetime.LiveTime
 */
export class LiveTime {

    /**
     * @constructs
     * @param {Function} fetch returns a promise that resolves to the current time, in seconds since Epoch
     * @param {Function} show receives the formatted time to display
     */
    constructor(fetch, show) {
        this._fetch = fetch
        this._show = show
        this._timestamp = null
        this._fetching = false
        this._refreshIntervalHandle = null
        this._tickIntervalHandle = null
    }

    /**
     * Set the time currently known, in seconds since Epoch.
     * @param {?Number} timestamp
     */
    setTimestamp(timestamp) {
        this._timestamp = timestamp
    }

    /**
     * Start refreshing and ticking.
     */
    start() {
        if (this._tickIntervalHandle) {
            return
        }

        this._refreshIntervalHandle = setInterval(() => this._refresh(), REFRESH_INTERVAL)
        this._tickIntervalHandle = setInterval(() => this._show(formatTimeAgo(this._timestamp)), TICK_INTERVAL)
    }

    /**
     * Stop refreshing and ticking.
     */
    stop() {
        clearInterval(this._refreshIntervalHandle)
        clearInterval(this._tickIntervalHandle)
        this._refreshIntervalHandle = null
        this._tickIntervalHandle = null
    }

    _refresh() {
        if (this._fetching) {
            return /* a slow device; don't pile up requests */
        }

        this._fetching = true
        this._fetch().then(function (timestamp) {
            if (timestamp !== undefined) {
                this._timestamp = timestamp
            }
        }.bind(this)).catch(function () {
            /* Keep showing the last known time; the next refresh tries again */
        }).finally(function () {
            this._fetching = false
        }.bind(this))
    }

}

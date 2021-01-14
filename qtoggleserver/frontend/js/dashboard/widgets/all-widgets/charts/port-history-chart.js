
import Logger from '$qui/lib/logger.module.js'

import {gettext}         from '$qui/base/i18n.js'
import Config            from '$qui/config.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {ComboField}      from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import {UpDownField}     from '$qui/forms/common-fields/common-fields.js'
import * as ArrayUtils   from '$qui/utils/array.js'
import * as ObjectUtils  from '$qui/utils/object.js'
import * as StringUtils  from '$qui/utils/string.js'

import * as ChartJS from '$app/lib/chartjs.module.js'

import * as PortsAPI                    from '$app/api/ports.js'
import * as Cache                       from '$app/cache.js'
import HistoryDownloadManager           from '$app/common/history-download-manager.js'
import {HistoryDownloadTooManyRequests} from '$app/common/history-download-manager.js'
import PortPickerField                  from '$app/dashboard/widgets/port-picker-field.js'
import {DEFAULT_COLOR}                  from '$app/dashboard/widgets/widget.js'

import {BaseChartWidget}     from './base-chart-widget.js'
import {BaseChartConfigForm} from './base-chart-widget.js'


const TIME_INTERVAL_CHOICES = [
    {label: gettext('1 second'), value: 1},
    {label: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 5}), value: 5},
    {label: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 10}), value: 10},
    {label: StringUtils.formatPercent(gettext('%(count)d seconds'), {count: 30}), value: 30},
    {label: gettext('1 minute'), value: 60},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 5}), value: 300},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 10}), value: 600},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 15}), value: 900},
    {label: StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 30}), value: 1800},
    {label: gettext('1 hour'), value: 3600},
    {label: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 4}), value: 14400},
    {label: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 8}), value: 28800},
    {label: StringUtils.formatPercent(gettext('%(count)d hours'), {count: 12}), value: 43200},
    {label: gettext('1 day'), value: 86400},
    {label: gettext('1 week'), value: 86400 * 7},
    {label: gettext('1 month'), value: 86400 * 31},
    {label: gettext('1 year'), value: 86400 * 366}
]

const TIME_GROUPS_CHOICES = [
    {label: `${gettext('1 minute')} (${gettext('every second')})`, value: {multiplier: 60, unit: 'second'}},
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 5})} (${gettext('every minute')})`,
        value: {multiplier: 5, unit: 'minute'}
    },
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 10})} (${gettext('every minute')})`,
        value: {multiplier: 10, unit: 'minute'}
    },
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 15})} (${gettext('every minute')})`,
        value: {multiplier: 15, unit: 'minute'}
    },
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d minutes'), {count: 30})} (${gettext('every minute')})`,
        value: {multiplier: 30, unit: 'minute'}
    },
    {label: `${gettext('1 hour')} (${gettext('every minute')})`, value: {multiplier: 60, unit: 'minute'}},
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d hours'), {count: 4})} (${gettext('every hour')})`,
        value: {multiplier: 4, unit: 'hour'}
    },
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d hours'), {count: 8})} (${gettext('every hour')})`,
        value: {multiplier: 8, unit: 'hour'}
    },
    {
        label: `${StringUtils.formatPercent(gettext('%(count)d hours'), {count: 12})} (${gettext('every hour')})`,
        value: {multiplier: 12, unit: 'hour'}
    },
    {label: `${gettext('1 day')} (${gettext('every hour')})`, value: {multiplier: 24, unit: 'hour'}},
    {label: `${gettext('1 week')} (${gettext('every day')})`, value: {multiplier: 7, unit: 'weekDay'}},
    {label: `${gettext('1 month')} (${gettext('every day')})`, value: {multiplier: 31, unit: 'day'}},
    {label: `${gettext('1 year')} (${gettext('every month')})`, value: {multiplier: 12, unit: 'month'}}
]

const UNIT_MAPPING = {
    weekDay: 'day'
}

const MAX_FETCH_REQUESTS = 5 /* This means at most 50k data points per interval */
const MAX_CACHED_SAMPLES_LEN = 400 /* Should be enough for every day during one year */

const logger = Logger.get('qtoggle.dashboard.widgets')


export class PortHistoryChartConfigForm extends BaseChartConfigForm {

    static BOOLEAN_FIELD_NAMES = ['inverted']
    static NUMBER_FIELD_NAMES = ['min', 'max', 'unit', 'multiplier', 'decimals']


    constructor({...args}) {
        super({
            fields: [
                new PortPickerField({
                    name: 'portId',
                    label: gettext('Port'),
                    required: true,
                    onChange: (value, form) => form.updateFieldsVisibility()
                }),
                new ColorComboField({
                    name: 'color',
                    filterEnabled: true,
                    label: gettext('Color'),
                    required: true
                }),
                new ComboField({
                    name: 'timeInterval',
                    label: gettext('Time Interval'),
                    required: true,
                    choices: TIME_INTERVAL_CHOICES
                }),
                new ComboField({
                    name: 'timeGroups',
                    label: gettext('Time Groups'),
                    required: true,
                    choices: TIME_GROUPS_CHOICES
                }),
                new NumericField({
                    name: 'max',
                    label: gettext('Maximum Value'),
                    description: gettext('Lower chart limit. Leave empty for automatic adjustment.')
                }),
                new NumericField({
                    name: 'min',
                    label: gettext('Minimum Value'),
                    description: gettext('Higher chart limit. Leave empty for automatic adjustment.')
                }),
                new TextField({
                    name: 'unit',
                    label: gettext('Unit'),
                    maxLength: 16
                }),
                new NumericField({
                    name: 'multiplier',
                    label: gettext('Multiplier'),
                    description: gettext('A multiplying factor for port values.'),
                    required: true
                }),
                new UpDownField({
                    name: 'decimals',
                    label: gettext('Decimals'),
                    min: 0,
                    max: 10
                }),
                new CheckField({
                    name: 'inverted',
                    label: gettext('Inverted Logic')
                })
            ],
            ...args
        })
    }

    /**
     * @returns {Boolean}
     */
    isBoolean() {
        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)
        let isBoolean = true
        if (port && port.type === 'number') {
            isBoolean = false
        }

        return isBoolean
    }

    updateFieldsVisibility() {
        if (this.isBoolean()) {
            this.constructor.NUMBER_FIELD_NAMES.forEach(function (name) {
                this.getField(name).hide()
            }, this)
            this.constructor.BOOLEAN_FIELD_NAMES.forEach(function (name) {
                this.getField(name).show()
            }, this)
        }
        else {
            this.constructor.BOOLEAN_FIELD_NAMES.forEach(function (name) {
                this.getField(name).hide()
            }, this)
            this.constructor.NUMBER_FIELD_NAMES.forEach(function (name) {
                this.getField(name).show()
            }, this)
        }
    }

    onUpdateFromWidget() {
        this.updateFieldsVisibility()
    }

    fromPort(port, fieldName) {
        let data = super.fromPort(port, fieldName)

        data.unit = port.unit
        data.min = port.min != null ? port.min : null
        data.max = port.max != null ? port.max : null

        return data
    }

}


/**
 * @alias qtoggle.dashboard.widgets.charts.PortHistoryChart
 * @extends qtoggle.dashboard.widgets.charts.BaseChartWidget
 */
export class PortHistoryChart extends BaseChartWidget {

    static ConfigForm = PortHistoryChartConfigForm


    /**
     * @constructs
     */
    constructor() {
        super()

        this._portId = ''
        this._color = DEFAULT_COLOR
        this._timeInterval = null
        this._timeGroups = null
        this._min = null
        this._max = null
        this._unit = ''
        this._multiplier = 1
        this._decimals = 0
        this._inverted = false

        this._fetchHistoryPromise = null
        this._historyDownloadManager = null /* Used for slice history mode */
        this._cachedSamples = [] /* Used for timestamps history mode */
        this._lastCachedTimestamp = 0 /* The requested timestamp of the last cached value */

        /* Use ChartJS date adapter to determine beginning of time units */
        this._dateAdapter = new ChartJS._adapters._date()
    }

    static isEnabled() {
        return Config.historyEnabled
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.online !== false)
    }

    /**
     * @returns {Boolean}
     */
    isBoolean() {
        let port = this.getPort(this._portId)
        return port && port.type === 'boolean'
    }

    /**
     * @returns {Boolean}
     */
    isSliceHistoryMode() {
        /* Override in concrete class */
        return true
    }

    /**
     * @returns {Boolean}
     */
    isInverted() {
        return this._inverted
    }

    /**
     * @returns {?Number}
     */
    getMin() {
        return this._min
    }

    /**
     * @returns {?Number}
     */
    getMax() {
        return this._max
    }

    /**
     * @returns {String}
     */
    getUnit() {
        return this._unit
    }

    /**
     * @returns {Number}
     */
    getMultiplier() {
        return this._multiplier
    }

    /**
     * @returns {Number}
     */
    getDecimals() {
        return this._decimals
    }

    /**
     * @returns {?{multiplier: Number, unit: String}}
     */
    getTimeGroups() {
        return this._timeGroups
    }

    /**
     * @returns {?Number}
     */
    getTimeInterval() {
        return this._timeInterval
    }

    /**
     * @returns {Number}
     */
    getFromTimestamp() {
        let nowDate = new Date()

        if (this._timeInterval != null) {
            return nowDate.getTime() - this._timeInterval * 1000
        }
        else if (this._timeGroups != null) {
            let {multiplier, unit} = this._timeGroups
            unit = UNIT_MAPPING[unit] || unit

            let timestamp = this._dateAdapter.endOf(nowDate, unit).getTime() + 1
            return this._dateAdapter.add(timestamp, -multiplier - 1, unit).getTime()
        }
        else {
            return nowDate.getTime()
        }
    }

    invalidateCache() {
        this._historyDownloadManager = null
        this._cachedSamples = []
        this._lastCachedTimestamp = 0
    }

    showCurrentValue(wantProgress = true) {
        if (wantProgress && !this._fetchHistoryPromise) {
            this.setProgress()
        }

        let fetchHistoryPromise
        let from, to, timestamps
        let sliceHistoryMode = this.isSliceHistoryMode()

        if (sliceHistoryMode) {
            from = this.getFromTimestamp()
            to = new Date().getTime()
            fetchHistoryPromise = this.getHistorySlice(from, to)
        }
        else {
            timestamps = this.computeGroupsTimestamps()
            fetchHistoryPromise = this.getHistoryTimestamps(timestamps)
        }

        fetchHistoryPromise.then(function (history) {

            if (!this._fetchHistoryPromise) {
                this.clearProgress()
            }

            let addedToDOM = this.getHTML().parents('body').length > 0
            if (!addedToDOM) {
                return /* The widget has been removed from DOM, in the meantime */
            }

            if (sliceHistoryMode) {
                this.showHistorySlice(history, from, to)
            }
            else {
                this.showHistoryTimestamps(history, timestamps)
            }

        }.bind(this)).catch(function (error) {

            if (error instanceof HistoryDownloadTooManyRequests) {
                let msg = gettext('Please choose a smaller interval of time!')
                logger.warn('too many requests while downloading history')
                error = msg
            }
            else {
                logger.errorStack(`fetching history for port ${this._portId} failed`, error)
            }

            this.setError(error)

        }.bind(this))
    }

    onPortValueChange(portId, value) {
        if (portId !== this._portId) {
            return
        }

        if (!this.getPanel().isActive()) {
            return
        }

        if (this._fetchHistoryPromise) {
            return /* Don't add data point if we're currently fetching history */
        }

        let wantProgress = false

        if (this.isSliceHistoryMode()) {
            if (!this._historyDownloadManager) {
                return
            }

            /* Remove old values that are no longer displayed on chart */
            let to = this.getFromTimestamp()
            this._historyDownloadManager.purge(null, to)

            /* Add new value using the current timestamp */
            this._historyDownloadManager.addSample(value, new Date().getTime(), /* bridgeGap = */ true)
        }
        else {
            /* Remove old values that will no longer be displayed on chart */

            while (this._cachedSamples.length > MAX_CACHED_SAMPLES_LEN) {
                this._cachedSamples.shift()
            }
        }

        this.showCurrentValue(wantProgress)
    }

    onPanelBecomeActive() {
        if (this.getPanel().isEditEnabled()) {
            return
        }

        this.invalidateCache()
        this.showCurrentValue()
    }

    configToJSON() {
        return {
            portId: this._portId,
            color: this._color,
            timeInterval: this._timeInterval,
            timeGroups: this._timeGroups,
            min: this._min,
            max: this._max,
            unit: this._unit,
            multiplier: this._multiplier,
            decimals: this._decimals,
            inverted: this._inverted
        }
    }

    configFromJSON(json) {
        /* Invalidate history if port changed */
        if (json.portId !== this._portId) {
            this.invalidateCache()
        }
        /* Invalidate history if time groups changed */
        if (json.timeGroups !== this._timeGroups) {
            this.invalidateCache()
        }

        if (json.portId) {
            this._portId = json.portId
        }
        if (json.color) {
            this._color = json.color
        }
        if (json.timeInterval) {
            this._timeInterval = json.timeInterval
        }
        if (json.timeGroups) {
            this._timeGroups = json.timeGroups
        }
        if (json.min !== undefined) {
            this._min = json.min
        }
        if (json.max !== undefined) {
            this._max = json.max
        }
        if (json.unit != null) {
            this._unit = json.unit
        }
        if (json.multiplier != null) {
            this._multiplier = json.multiplier
        }
        if (json.decimals != null) {
            this._decimals = json.decimals
        }
        if (json.inverted != null) {
            this._inverted = json.inverted
        }
    }

    computeGroupsTimestamps() {
        if (this._timeGroups == null) {
            return []
        }

        let timestamps = []
        let {multiplier, unit} = this._timeGroups
        unit = UNIT_MAPPING[unit] || unit

        let nowDate = new Date()
        let timestamp = this._dateAdapter.endOf(nowDate, unit).getTime() + 1
        timestamps.push(timestamp)

        for (let i = 0; i < multiplier; i++) {
            timestamp = this._dateAdapter.add(timestamp, -1, unit).getTime()
            timestamps.push(timestamp)
        }

        timestamps.reverse()

        return timestamps
    }

    getHistorySlice(from, to) {
        if (!this._portId) {
            return Promise.resolve([])
        }

        let currentFetchPromise = this._fetchHistoryPromise || Promise.resolve()
        let fetchPromise = currentFetchPromise.then(function () {

            if (!this._historyDownloadManager) {
                this._historyDownloadManager = new HistoryDownloadManager(this.getPort(this._portId))
            }
            return this._historyDownloadManager.fetch(Math.round(from), Math.round(to), MAX_FETCH_REQUESTS)

        }.bind(this)).catch(function (error) {

            this._fetchHistoryPromise = null
            throw error

        }.bind(this)).then(function (history) {

            if (this._fetchHistoryPromise === fetchPromise) {
                /* Last active fetch promise has just ended */
                this._fetchHistoryPromise = null
            }

            return history

        }.bind(this))

        this._fetchHistoryPromise = fetchPromise

        return this._fetchHistoryPromise
    }

    getHistoryTimestamps(timestamps) {
        /* Ensure requested timestamps are chronologically ordered */
        timestamps = timestamps.slice()
        timestamps.sort()

        if (!timestamps.length) {
            return Promise.resolve([])
        }

        let currentFetchPromise = this._fetchHistoryPromise || Promise.resolve()
        let now = new Date().getTime()
        let port = Cache.getPort(this._portId)
        let currentValue = port.value
        let timestampsToFetch = [] /* Will be assigned later, in promise */

        let fetchPromise = currentFetchPromise.then(function () {

            /* Only fetch samples for timestamps newer than last cached sample */
            timestampsToFetch = timestamps.filter(t => t > this._lastCachedTimestamp)

            /* Only fetch samples for timestamps from the past */
            timestampsToFetch = timestampsToFetch.filter(t => t < now)

            if (timestampsToFetch.length > 0) {
                return PortsAPI.getPortHistory(
                    this._portId,
                    /* from = */ null,
                    /* to = */ null,
                    /* limit = */ null,
                    timestampsToFetch
                )
            }
            else {
                return Promise.resolve([])
            }

        }.bind(this)).catch(function (error) {

            this._fetchHistoryPromise = null
            throw error

        }.bind(this)).then(function (history) {

            /* Keep only non-null samples newer than last cached sample */
            if (this._cachedSamples.length) {
                let lastCachedSample = this._cachedSamples[this._cachedSamples.length - 1]
                history = history.filter(s => s != null && s.timestamp > lastCachedSample.timestamp)
            }
            else {
                history = history.filter(s => s != null)
            }

            if (history.length && timestampsToFetch.length) {
                this._lastCachedTimestamp = timestampsToFetch[timestampsToFetch.length - 1]
            }

            /* Ignore duplicate (and successive) samples */
            let distinctHistory = history.slice(0, 1)
            history.slice(1).forEach(function (sample, i) {
                let prevSample = history[i]
                if (sample.timestamp !== prevSample.timestamp) {
                    distinctHistory.push(sample)
                }
            })
            history = distinctHistory

            /* Cache fetched values */
            this._cachedSamples = this._cachedSamples.concat(history)

            if (this._fetchHistoryPromise === fetchPromise) {
                /* Last active fetch promise has just ended */
                this._fetchHistoryPromise = null
            }

            if (this._cachedSamples.length === 0) {
                return ArrayUtils.range(0, timestamps.length).map(() => null)
            }

            /* Associate samples to requested timestamps */
            let selectedSamples = []
            let samples = this._cachedSamples.slice()

            /* Consider current value as well, if available */
            if (currentValue != null) {
                samples.push({value: currentValue, timestamp: now})
            }

            for (let timestampIndex = timestamps.length - 1; timestampIndex >= 0; timestampIndex--) {
                let timestamp = timestamps[timestampIndex]

                while (samples.length && samples[samples.length - 1].timestamp > timestamp) {
                    samples.pop()
                }

                if (!samples.length) {
                    break /* No more samples */
                }

                selectedSamples.push(samples[samples.length - 1])
            }

            /* Pad with nulls until we get our requested number of samples */
            while (selectedSamples.length < timestamps.length) {
                selectedSamples.push(null)
            }

            /* We actually built selected samples in reverse order */
            selectedSamples.reverse()

            return selectedSamples

        }.bind(this))

        this._fetchHistoryPromise = fetchPromise

        return this._fetchHistoryPromise
    }

    /**
     * @param {Object[]} history
     * @param {Number} from
     * @param {Number} to
     */
    showHistorySlice(history, from, to) {
        /* Override in concrete class */
    }

    /**
     * @param {Object[]} history
     * @param {Number[]} timestamps
     */
    showHistoryTimestamps(history, timestamps) {
        /* Override in concrete class */
    }

    /**
     * Prepare value for chart by multiplying and rounding it.
     * @param {Number} value
     * @returns {Number}
     */
    prepareNumericValue(value) {
        /* Multiply and round value to indicated number of decimals */
        return Number((value * this._multiplier).toFixed(this._decimals))
    }

    makeChartOptions() {
        return ObjectUtils.combine(super.makeChartOptions(), {
            colors: [this._color]
        })
    }

}


import Logger from '$qui/lib/logger.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {ComboField}      from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import * as StringUtils  from '$qui/utils/string.js'

import * as ChartJS from '$app/lib/chartjs.module.js'

import * as PortsAPI                    from '$app/api/ports.js'
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
    {label: `${gettext('1 week')} (${gettext('every day')})`, value: {interval: 86400 * 7, unit: 'day'}},
    {label: `${gettext('1 month')} (${gettext('every day')})`, value: {interval: 86400 * 31, unit: 'day'}},
    {label: `${gettext('1 year')} (${gettext('every month')})`, value: {interval: 86400 * 366, unit: 'month'}}
]

const MAX_FETCH_REQUESTS = 5 /* This means at most 50k data points per interval */

const logger = Logger.get('qtoggle.dashboard.widgets')


export class PortHistoryChartConfigForm extends BaseChartConfigForm {

    static BOOLEAN_FIELD_NAMES = ['inverted']
    static NUMBER_FIELD_NAMES = ['min', 'max', 'unit']


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
                new CheckField({
                    name: 'inverted',
                    label: gettext('Inverted Logic')
                })
            ],
            ...args
        })
    }

    updateFieldsVisibility() {
        let data = this.getUnvalidatedData()
        let port = this.getPort(data.portId)
        let isBoolean = true
        if (port && port.type === 'number') {
            isBoolean = false
        }

        if (isBoolean) {
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

}


/**
 * @alias qtoggle.dashboard.widgets.charts.PortHistoryChart
 * @extends qtoggle.dashboard.widgets.charts.BaseChartWidget
 */
export class PortHistoryChart extends BaseChartWidget {

    static ConfigForm = PortHistoryChartConfigForm
    static vResizable = true
    static hResizable = true
    static hasFrame = true


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
        this._inverted = false

        this._fetchHistoryPromise = null
        this._historyDownloadManager = null /* Used for slice history mode */
        this._cachedSamples = [] /* Used for timestamps history mode */
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

    showCurrentValue(wantProgress = true) {
        if (wantProgress && !this._fetchHistoryPromise) {
            this.setProgress()
        }

        let fetchHistoryPromise
        let from, to, timestamps
        let sliceHistoryMode = this.isSliceHistoryMode()

        if (sliceHistoryMode) {
            from = new Date().getTime() - this._timeInterval * 1000
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

        if (this._fetchHistoryPromise) {
            return /* Don't add data point if we're currently fetching history */
        }

        let wantProgress = false

        if (this.isSliceHistoryMode()) {
            if (!this._historyDownloadManager) {
                return
            }

            /* Remove old values that are no longer displayed on chart */
            let to = new Date().getTime() - this._timeInterval * 1000 * 1.1 /* Extra 10% safety margin */
            this._historyDownloadManager.purge(null, to)

            /* Add new value using the current timestamp */
            this._historyDownloadManager.addSample(value, new Date().getTime(), /* bridgeGap = */ true)
        }
        else {
            /* Remove old values that are no longer displayed on chart */
            let {multiplier, unit} = this._timeGroups

            /* Use ChartJS date adapter to determine beginning of time units */
            let adapter = new ChartJS._adapters._date()

            let nowDate = new Date()
            let timestamp = adapter.endOf(nowDate, unit).getTime() + 1
            let firstTimestamp = adapter.add(timestamp, -multiplier - 1, unit).getTime()

            while (this._cachedSamples.length > 0 && this._cachedSamples[0].timestamp < firstTimestamp) {
                this._cachedSamples.shift()
            }
        }

        this.showCurrentValue(wantProgress)
    }

    onPanelBecomeActive() {
        if (this.getPanel().isEditEnabled()) {
            return
        }

        this._historyDownloadManager = null
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
            inverted: this._inverted
        }
    }

    configFromJSON(json) {
        /* Invalidate history if port changed */
        if (json.portId !== this._portId) {
            this._historyDownloadManager = null
            this._cachedSamples = []
        }

        /* Invalidate cached samples if time groups changed */
        if (json.timeGroups !== this._timeGroups) {
            this._cachedSamples = []
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

        /* Use ChartJS date adapter to determine beginning of time units */
        let adapter = new ChartJS._adapters._date()

        let nowDate = new Date()
        let timestamp = adapter.endOf(nowDate, unit).getTime() + 1
        timestamps.push(timestamp)

        for (let i = 0; i < multiplier; i++) {
            timestamp = adapter.add(timestamp, -1, unit).getTime()
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

        /* Only fetch samples for timestamps newer than last cached sample */
        let lastFetchedTimestamp = 0
        if (this._cachedSamples.length > 0) {
            lastFetchedTimestamp = this._cachedSamples[this._cachedSamples.length - 1].timestamp
        }

        let timestampsToFetch = timestamps.filter(t => t > lastFetchedTimestamp)
        let currentFetchPromise = this._fetchHistoryPromise || Promise.resolve()

        let fetchPromise = currentFetchPromise.then(function () {

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

            /* Cache fetched values */
            this._cachedSamples = this._cachedSamples.concat(history)

            if (this._fetchHistoryPromise === fetchPromise) {
                /* Last active fetch promise has just ended */
                this._fetchHistoryPromise = null
            }

            return history

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

    makeChartOptions() {
        let options = super.makeChartOptions()

        if (!this.isBoolean()) {
            options.yMin = this._min
            options.yMax = this._max
            options.unitOfMeasurement = this._unit
        }
        else {
            options.stepped = true
            options.yTicksStepSize = 1
            options.yTicksLabelCallback = value => value ? gettext('On') : gettext('Off')
        }

        options.colors = [this._color]

        return options
    }

}


import Logger from '$qui/lib/logger.module.js'

import {gettext}         from '$qui/base/i18n.js'
import {CheckField}      from '$qui/forms/common-fields/common-fields.js'
import {ColorComboField} from '$qui/forms/common-fields/common-fields.js'
import {ComboField}      from '$qui/forms/common-fields/common-fields.js'
import {NumericField}    from '$qui/forms/common-fields/common-fields.js'
import {TextField}       from '$qui/forms/common-fields/common-fields.js'
import * as StringUtils  from '$qui/utils/string.js'

import HistoryDownloadManager           from '$app/common/history-download-manager.js'
import {HistoryDownloadTooManyRequests} from '$app/common/history-download-manager.js'
import PortPickerField                  from '$app/dashboard/widgets/port-picker-field.js'
import {DEFAULT_COLOR}                  from '$app/dashboard/widgets/widget.js'
import {decimate}                       from '$app/utils.js'

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

const MAX_FETCH_REQUESTS = 5 /* This means at most 50k data points per interval */
const MAX_DATA_POINTS_LEN = 1000 /* Max data points to be displayed on chart at once */

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
                    onChange: (value, form) => form._showHidePortTypeFields()
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

    _showHidePortTypeFields() {
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
        this._showHidePortTypeFields()
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
        this._min = null
        this._max = null
        this._unit = ''
        this._inverted = false

        this._fetchHistoryPromise = null
        this._historyDownloadManager = null
    }

    isValid() {
        if (!this._portId) {
            return false
        }

        let port = this.getPort(this._portId)

        return Boolean(port && port.enabled && port.online !== false)
    }

    isBoolean() {
        let port = this.getPort(this._portId)
        return port && port.type === 'boolean'
    }

    showCurrentValue(wantProgress = true) {
        let from = new Date().getTime() - this._timeInterval * 1000
        let to = new Date().getTime()

        if (wantProgress && !this._fetchHistoryPromise) {
            this.setProgress()
        }

        this.getHistory(from, to).then(function (history) {

            if (!this._fetchHistoryPromise) {
                this.clearProgress()
            }
            this.showHistory(history, from, to)

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

        if (!this._historyDownloadManager) {
            return
        }

        if (this._fetchHistoryPromise) {
            return /* Don't add data point if we're currently fetching history */
        }

        let to = new Date().getTime() - this._timeInterval * 1000 * 1.1 /* Extra 10% safety margin */

        this._historyDownloadManager.purge(null, to)
        this._historyDownloadManager.addSample(value, new Date().getTime(), /* bridgeGap = */ true)

        let wantProgress = false
        /* Always show progress if we don't have cached data */
        if (!this._historyDownloadManager) {
            wantProgress = true
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

    getHistory(from, to) {
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

            this._fetchHistoryPromise = Promise.resolve()
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

    decimateHistory(history, from, to) {
        return decimate(history, MAX_DATA_POINTS_LEN, /* xField = */ 'timestamp', /* yField = */ 'value')
    }

    processHistory(history, from, to) {
        return history
    }

    showHistory(history, from, to) {
        let addedToDOM = this.getHTML().parents('body').length > 0
        if (!addedToDOM) {
            return
        }

        history = this.decimateHistory(history, from, to)
        history = this.processHistory(history, from, to)

        let data
        if (this.isBoolean()) {
            let low = this._inverted ? 1 : 0
            let high = this._inverted ? 0 : 1
            data = history.map(sample => [sample.timestamp, sample.value ? low : high])
        }
        else {
            /* Also round value to decent number of decimals */
            data = history.map(sample => [sample.timestamp, Math.round(sample.value * 1e6) / 1e6])
        }

        this.widgetCall('setValue', data)
        this.widgetCall('setXRange', from, to)
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
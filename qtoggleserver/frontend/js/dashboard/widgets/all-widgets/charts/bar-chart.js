
import {gettext}        from '$qui/base/i18n.js'
import {ComboField}     from '$qui/forms/common-fields/common-fields.js'
import StockIcon        from '$qui/icons/stock-icon.js'
import * as DateUtils   from '$qui/utils/date.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as Widgets from '$app/dashboard/widgets/widgets.js'

import '$app/widgets/bar-chart.js'

import {PortHistoryChartConfigForm} from './port-history-chart.js'
import {PortHistoryChart}           from './port-history-chart.js'


const BAR_INFO_CHOICES_NUMBER = [
    {label: gettext('Difference'), value: 'difference'},
    {label: gettext('Maximum'), value: 'maximum'},
    {label: gettext('Minimum'), value: 'minimum'},
    {label: gettext('Average'), value: 'average'}
]

const BAR_INFO_CHOICES_BOOLEAN = [
    {label: gettext('Changes'), value: 'changes'},
    {label: gettext('On Time'), value: 'on-time'},
    {label: gettext('Off Time'), value: 'off-time'}
]

const NO_SLICE_MODE_INFO = ['difference']

const DATE_FORMAT_BY_UNIT = {
    second: '%S',
    minute: '%H:%M',
    hour: '%H:00',
    day: '%d',
    weekDay: '%a',
    month: '%b'
}


class ConfigForm extends PortHistoryChartConfigForm {

    constructor({...args}) {
        super({...args})

        let index = this.getFieldIndex('timeInterval')
        this.addField(
            index,
            new ComboField({
                name: 'barInfo',
                label: gettext('Bar Information'),
                required: true,
                choices: []
            })
        )

        this.getField('timeInterval').hide()
    }

    updateFieldsVisibility() {
        super.updateFieldsVisibility()

        let choices = this.isBoolean() ? BAR_INFO_CHOICES_BOOLEAN : BAR_INFO_CHOICES_NUMBER
        this.getField('barInfo').setChoices(choices)
    }

}


/**
 * @alias qtoggle.dashboard.widgets.charts.BarChart
 * @extends qtoggle.dashboard.widgets.charts.PortHistoryChart
 */
class BarChart extends PortHistoryChart {

    static CHART_TYPE = 'bar'

    static displayName = gettext('Bar Chart')
    static typeName = 'BarChart'
    static icon = new StockIcon({name: 'widget-bar-chart', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm


    /**
     * @constructs
     */
    constructor() {
        super()

        this._barInfo = null
    }

    configToJSON() {
        return ObjectUtils.combine(super.configToJSON(), {
            barInfo: this._barInfo
        })
    }

    configFromJSON(json) {
        super.configFromJSON(json)

        /* Invalidate cached samples if bar info changed */
        if (json.barInfo !== this._barInfo) {
            this.invalidateCache()
        }

        if (json.barInfo != null) {
            this._barInfo = json.barInfo
        }
    }

    isSliceHistoryMode() {
        return !NO_SLICE_MODE_INFO.includes(this._barInfo)
    }

    showHistorySlice(history, from, to) {
        let fullTimestamps = this.computeGroupsTimestamps() /* Including ending timestamp, normally from the future */
        let timestamps = fullTimestamps.slice(0, -1) /* Exclude last timestamp, from the future */

        /* Invert boolean signal, if needed */
        if (this.isBoolean() && this.isInverted()) {
            history = history.map(function (sample) {
                sample = ObjectUtils.copy(sample)
                sample.value = !sample.value

                return sample
            })
        }
        else {
            history = history.slice() /* Work on copy to be able to remove from array */
        }

        let categories = this.makeBarCategories(timestamps)
        let data = timestamps.map(function (timestamp, i) {

            /* Compute bar history slice */
            let nextTimestamp = i < timestamps.length - 1 ? timestamps[i + 1] : Infinity
            let barHistory = []
            while (history.length > 0 && history[0].timestamp < timestamp) {
                history.shift()
            }
            while (history.length > 0 && history[0].timestamp < nextTimestamp) {
                barHistory.push(history.shift())
            }

            let value = this.computeBarValue(barHistory, fullTimestamps[i], fullTimestamps[i + 1])

            return this.prepareNumericValue(value)

        }.bind(this))

        this.widgetCall('setValue', data)
        this.widgetCall({categories: categories})
    }

    showHistoryTimestamps(history, timestamps) {
        timestamps = timestamps.slice(0, -1) /* Last timestamp is in the future */

        let categories = this.makeBarCategories(timestamps)
        let data = timestamps.map(function (timestamp, i) {

            if (history[i] == null || history[i + 1] == null) {
                return 0
            }

            let barHistory = [history[i], history[i + 1]]
            let value = this.computeBarValue(barHistory)

            return this.prepareNumericValue(value)

        }.bind(this))

        this.widgetCall('setValue', data)
        this.widgetCall({categories: categories})
    }

    makeBarCategories(timestamps) {
        let {unit} = this.getTimeGroups()
        let format = DATE_FORMAT_BY_UNIT[unit]

        return timestamps.map(function (timestamp) {
            return DateUtils.formatPercent(new Date(timestamp), format)
        })
    }

    computeBarValue(history, from, to) {
        if (history.length === 0) {
            return 0
        }

        switch (this._barInfo) {
            case 'difference':
                return history[history.length - 1].value - history[0].value

            case 'maximum':
                return history.reduce((a, s) => Math.max(s.value, a), -Infinity)

            case 'minimum':
                return history.reduce((a, s) => Math.min(s.value, a), Infinity)

            case 'average':
                return history.reduce((a, s) => s.value + a, 0) / history.length

            case 'changes': {
                let changes = 0
                let lastValue = history[0].value
                history.forEach(function ({value}) {
                    if (value !== lastValue) {
                        changes += 1
                    }

                    lastValue = value
                })

                return changes
            }

            case 'on-time':
            case 'off-time': {
                let duration = 0
                let lastValue = null
                let lastStartTimestamp = null
                let onTime = this._barInfo === 'on-time'

                if (Boolean(history[0].value) !== onTime) {
                    duration += history[0].timestamp - from
                }

                history.forEach(function ({value, timestamp}) {
                    if (value === lastValue) {
                        return
                    }

                    if (Boolean(value) === onTime) { /* Start time measurement */
                        lastStartTimestamp = timestamp
                    }
                    else if (lastStartTimestamp != null) { /* Stop time measurement */
                        duration += timestamp - lastStartTimestamp
                        lastStartTimestamp = null
                    }
                })

                /* Add remaining duration */
                if (lastStartTimestamp != null) {
                    duration += to - lastStartTimestamp
                }

                return duration
            }
        }

        return 0
    }

    makeChartOptions() {
        let options = ObjectUtils.combine(super.makeChartOptions(), {
            allowTickRotation: true
        })

        if (!this.isBoolean()) {
            options.yMin = this.getMin()
            options.yMax = this.getMax()
            options.unitOfMeasurement = this.getUnit()
        }

        if (this._barInfo === 'on-time' || this._barInfo === 'off-time') {
            options.yTicksLabelCallback = function (value) {
                let format = '%H:%M:%S'
                if (value >= 24 * 3600 * 1000) {
                    format = `%d ${gettext('days')}, ${format}`
                }

                return DateUtils.formatDurationPercent(value, format)
            }
        }

        return options
    }

    makePadding() {
        return {
            top: 0.2,
            right: 0,
            bottom: 0,
            left: 0
        }
    }

}

Widgets.register(BarChart)


export default BarChart

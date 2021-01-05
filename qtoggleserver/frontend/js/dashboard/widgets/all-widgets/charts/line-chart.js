
import {gettext}            from '$qui/base/i18n.js'
import {CheckField}         from '$qui/forms/common-fields/common-fields.js'
import {ChoiceButtonsField} from '$qui/forms/common-fields/common-fields.js'
import StockIcon            from '$qui/icons/stock-icon.js'
import * as ObjectUtils     from '$qui/utils/object.js'

import * as Widgets    from '$app/dashboard/widgets/widgets.js'
import {decimate}      from '$app/utils.js'
import {movingAverage} from '$app/utils.js'

import '$app/widgets/time-chart.js'


import {PortHistoryChartConfigForm} from './port-history-chart.js'
import {PortHistoryChart}           from './port-history-chart.js'


const FILTER_LEN_RATIO = { /* Filter window length as percent of total signal length */
    0: 0,
    1: 0.025,
    2: 0.075,
    3: 0.2
}

const MAX_DATA_POINTS_LEN = 1000 /* Max data points to be displayed on chart at once */


class ConfigForm extends PortHistoryChartConfigForm {

    static NUMBER_FIELD_NAMES = ['min', 'max', 'unit', 'smoothLevel']

    constructor({...args}) {
        super({...args})

        this.addField(-1, new ChoiceButtonsField({
            name: 'smoothLevel',
            label: gettext('Smoothing'),
            separator: true,
            choices: [
                {value: 0, label: gettext('Off')},
                {value: 1, label: gettext('Slight')},
                {value: 2, label: gettext('Medium')},
                {value: 3, label: gettext('Strong')}
            ]
        }))
        this.addField(-1, new CheckField({
            name: 'fillArea',
            label: gettext('Fill Area')
        }))
        this.addField(-1, new CheckField({
            name: 'showDataPoints',
            label: gettext('Show Data Points')
        }))

        this.getField('timeGroups').hide()
    }

}


/**
 * @alias qtoggle.dashboard.widgets.charts.LineChart
 * @extends qtoggle.dashboard.widgets.charts.PortHistoryChart
 */
class LineChart extends PortHistoryChart {

    static CHART_TYPE = 'time'

    static displayName = gettext('Line Chart')
    static typeName = 'LineChart'
    static icon = new StockIcon({name: 'widget-line-chart', stockName: 'qtoggle'})
    static ConfigForm = ConfigForm


    /**
     * @constructs
     */
    constructor() {
        super()

        this._smoothLevel = 0
        this._fillArea = false
        this._showDataPoints = false
    }

    configToJSON() {
        return ObjectUtils.combine(super.configToJSON(), {
            smoothLevel: this._smoothLevel,
            fillArea: this._fillArea,
            showDataPoints: this._showDataPoints
        })
    }

    configFromJSON(json) {
        super.configFromJSON(json)

        if (json.smoothLevel != null) {
            this._smoothLevel = json.smoothLevel
        }
        if (json.fillArea != null) {
            this._fillArea = json.fillArea
        }
        if (json.showDataPoints != null) {
            this._showDataPoints = json.showDataPoints
        }
    }

    decimateHistory(history, from, to) {
        return decimate(history, MAX_DATA_POINTS_LEN, /* xField = */ 'timestamp', /* yField = */ 'value')
    }

    processHistory(history, from, to) {
        /* Apply moving average filtering in addition to chart smoothing */
        if (!this.isBoolean() && this._smoothLevel) {
            history = this.applyMovingAverage(history)
        }

        return history
    }

    applyMovingAverage(history) {
        let wLength = Math.round(history.length * FILTER_LEN_RATIO[this._smoothLevel])
        if (wLength < 2) {
            return history
        }

        return movingAverage(history, wLength, /* xField = */ 'timestamp', /* yField = */ 'value')
    }

    isSliceHistoryMode() {
        return true
    }

    showHistorySlice(history, from, to) {
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
            options.smooth = Boolean(this._smoothLevel)
            options.fillArea = this._fillArea
            options.showDataPoints = this._showDataPoints
        }

        options.showMajorTicks = true

        return options
    }

}

Widgets.register(LineChart)


export default LineChart

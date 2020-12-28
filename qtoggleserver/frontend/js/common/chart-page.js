
import $ from '$qui/lib/jquery.module.js'

import {gettext}             from '$qui/base/i18n.js'
import {mix}                 from '$qui/base/mixwith.js'
import {CheckField}          from '$qui/forms/common-fields/common-fields.js'
import {ChoiceButtonsField}  from '$qui/forms/common-fields/common-fields.js'
import {NumericField}        from '$qui/forms/common-fields/common-fields.js'
import {OptionsForm}         from '$qui/forms/common-forms/common-forms.js'
import StockIcon             from '$qui/icons/stock-icon.js'
import {StructuredPageMixin} from '$qui/pages/common-pages/common-pages.js'
import * as ObjectUtils      from '$qui/utils/object.js'
import {ProgressViewMixin}   from '$qui/views/common-views/common-views.js'
import * as Window           from '$qui/window.js'

import * as Cache from '$app/cache.js'

import '$app/widgets/bar-chart.js'
import '$app/widgets/line-chart.js'
import '$app/widgets/pie-chart.js'
import '$app/widgets/time-chart.js'


const MAX_DATA_POINT_LEN = 1000


/**
 * @alias qtoggle.common.ChartPageOptionsForm
 * @extends qui.forms.commonforms.OptionsForm
 */
export class ChartPageOptionsForm extends OptionsForm {

    /**
     * @constructs
     * @param {qtoggle.common.ChartPage} chartPage
     * @param {Boolean} [enableSmooth]
     * @param {Boolean} [enableFillArea]
     * @param {Boolean} [enableShowDataPoints]
     * @param {Boolean} [enableMinMax]
     * @param {?String} [prefsPrefix]
     * @param {Object} [defaults]
     */
    constructor({
        chartPage,
        enableSmooth = true,
        enableFillArea = true,
        enableShowDataPoints = true,
        enableMinMax = false,
        prefsPrefix = null,
        defaults = {}
    }) {

        let fields = []
        if (enableSmooth) {
            fields.push(new CheckField({
                name: 'smooth',
                label: gettext('Smooth Lines')
            }))
        }
        if (enableFillArea) {
            fields.push(new CheckField({
                name: 'fillArea',
                label: gettext('Fill Area')
            }))
        }
        if (enableShowDataPoints) {
            fields.push(new ChoiceButtonsField({
                name: 'showDataPoints',
                label: gettext('Show Data Points'),
                choices: [
                    {value: false, label: gettext('Off')},
                    {value: null, label: gettext('Auto')},
                    {value: true, label: gettext('On')}
                ]
            }))
        }
        if (enableMinMax) {
            fields.push(new NumericField({
                name: 'max',
                label: gettext('Maximum'),
                description: gettext('Higher chart limit. Clear value for automatic adjustment.'),
                required: false
            }))
            fields.push(new NumericField({
                name: 'min',
                label: gettext('Minimum'),
                description: gettext('Lower chart limit. Clear value for automatic adjustment.'),
                required: false
            }))
        }

        let initialData = defaults
        if (prefsPrefix) {
            Object.assign(initialData, Cache.getPrefs(prefsPrefix, {}))
        }

        super({
            page: chartPage,
            fields: fields,
            initialData: initialData
        })

        this._prefsPrefix = prefsPrefix
    }

    init() {
        this.updateFieldsVisibility()
        this.getData().then(data => this.getPage().updateOptions(data))
    }

    onChange(data, fieldName) {
        if (this._prefsPrefix) {
            Cache.setPrefs(`${this._prefsPrefix}.${fieldName}`, data[fieldName])
        }

        this.updateFieldsVisibility()
        this.getPage().updateOptions(data)
    }

    updateFieldsVisibility() {
    }

}

/**
 * @alias qtoggle.common.ChartPage
 * @mixes qui.pages.StructuredPageMixin
 */
class ChartPage extends mix().with(StructuredPageMixin, ProgressViewMixin) {

    /**
     * @constructs
     * @param {String} type chart type
     * @param {Object} [chartOptions] options to pass to chart widget
     * @param {Array} [data] initial chart data
     * @param {...*} args parent class parameters
     */
    constructor({type, chartOptions = {}, data = [], ...args}) {
        ObjectUtils.assignDefault(args, {
            popup: !Window.isSmallScreen(),
            transparent: false,
            closable: true,
            icon: new StockIcon({name: 'chart', stockName: 'qtoggle'}),
            verticallyCentered: true /* for ProgressViewMixin */
        })

        super(args)

        let aspectRatio
        if (Window.isSmallScreen()) {
            aspectRatio = 1
        }
        else {
            aspectRatio = Window.getWidth() / Window.getHeight() * 1.2
        }

        this._type = type
        this._chartOptions = ObjectUtils.combine(chartOptions, {
            onPanZoomStart: this.handlePanZoomStart.bind(this),
            onPanZoomEnd: this.handlePanZoomEnd.bind(this),
            aspectRatio: aspectRatio
        })
        this._data = data
        this.widgetCall = null

        let panZoomMode = this._chartOptions.panZoomMode
        if (panZoomMode) {
            if (panZoomMode.includes('x')) {
                delete this._chartOptions.xMin
                delete this._chartOptions.xMax
            }
            if (panZoomMode.includes('y')) {
                delete this._chartOptions.yMin
                delete this._chartOptions.yMax
            }
        }
    }

    initHTML(html) {
        super.initHTML(html)

        html.addClass('qtoggle-chart-page-view unexpanded')
    }

    makeBody() {
        let chartDiv = $('<div></div>', {class: 'qtoggle-chart-page-chart-container'})
        let widget = chartDiv[`${this._type}chart`]

        this.widgetCall = function (...args) {
            return widget.apply(chartDiv, args)
        }

        this.widgetCall(this._chartOptions)
        this.widgetCall('setValue', this._data)

        return chartDiv
    }

    makeOptionsBarContent() {
        return new ChartPageOptionsForm({chartPage: this})
    }

    /**
     * @param {Object} options
     */
    updateOptions(options) {
        let widgetOptions = {}

        if ('smooth' in options) {
            widgetOptions.smooth = options['smooth']
        }
        if ('fillArea' in options) {
            widgetOptions.fillArea = options['fillArea']
        }
        if ('showDataPoints' in options) {
            widgetOptions.showDataPoints = options['showDataPoints']
        }
        if (options['min'] != null) {
            widgetOptions.yMin = options['min']
        }
        else {
            widgetOptions.yMin = null
        }
        if (options['max'] != null) {
            widgetOptions.yMax = options['max']
        }
        else {
            widgetOptions.yMax = null
        }

        if (Object.keys(widgetOptions).length > 0) {
            this.widgetCall(widgetOptions)
        }
    }

    /**
     * @param {Number} xMin
     * @param {Number} xMax
     * @param {Number} yMin
     * @param {Number} yMax
     */
    handlePanZoomStart(xMin, xMax, yMin, yMax) {
    }

    /**
     * @param {Number} xMin
     * @param {Number} xMax
     * @param {Number} yMin
     * @param {Number} yMax
     */
    handlePanZoomEnd(xMin, xMax, yMin, yMax) {
    }

    /**
     * @param {*} data
     * @param {Boolean} [decimate]
     */
    setData(data, decimate = true) {
        this._data = data

        if (decimate && data.length > MAX_DATA_POINT_LEN) {
            data = this._decimate(data)
        }

        this.widgetCall('setValue', data)
    }

    /**
     * @returns {*}
     */
    getData() {
        return this._data
    }

    _decimate(data) {
        let windowSize = Math.ceil(data.length * 2 / MAX_DATA_POINT_LEN)
        let decimatedData = []
        for (let i = 0; i < MAX_DATA_POINT_LEN / 2; i++) {
            let win = data.slice(i * windowSize, (i + 1) * windowSize)
            if (!win.length) {
                break
            }
            let analysis = this._analyzeDecimationWindow(win)
            if (analysis.min[0] < analysis.max[0]) {
                decimatedData.push(analysis.min, analysis.max)
            }
            else {
                decimatedData.push(analysis.max, analysis.min)
            }
        }

        return decimatedData
    }

    _analyzeDecimationWindow(data) {
        // FIXME: this only analyzes the first series in data
        let [minX, minY] = data[0]
        let [maxX, maxY] = data[0]
        for (let i = 0; i < data.length; i++) {
            let d = data[i]
            let y = d[1]
            if (y < minY) {
                [minX, minY] = d
            }
            else if (y > maxY) {
                [maxX, maxY] = d
            }
        }

        return {
            min: [minX, minY],
            max: [maxX, maxY]
        }
    }

    /**
     * @returns {{min: Number, max: Number}}
     */
    getXRange() {
        return this.widgetCall('getXRange')
    }

    /**
     * @param {Number} xMin
     * @param {Number} xMax
     */
    setXRange(xMin, xMax) {
        return this.widgetCall('setXRange', xMin, xMax)
    }

    /**
     * @returns {{min: Number, max: Number}}
     */
    getYRange() {
        return this.widgetCall('getYRange')
    }

    /**
     * @param {Number} yMin
     * @param {Number} yMax
     */
    setYRange(yMin, yMax) {
        return this.widgetCall('setYRange', yMin, yMax)
    }

}


export default ChartPage

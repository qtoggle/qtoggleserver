
import $ from '$qui/lib/jquery.module.js'

import * as Theme       from '$qui/theme.js'
import * as Colors      from '$qui/utils/colors.js'
import * as CSS         from '$qui/utils/css.js'
import * as DateUtils   from '$qui/utils/date.js'
import * as ObjectUtils from '$qui/utils/object.js'
import * as BaseWidget  from '$qui/widgets/base-widget.js' /* Needed */
import * as Window      from '$qui/window.js'

import * as ChartJS from '$app/lib/chartjs.module.js'
import Hammer       from '$app/lib/hammer.module.js'

import '$app/lib/chartjs-plugin-zoom.js'
import '$node/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.js'


const DEFAULT_COLORS = [
    '@green-color',
    '@orange-color',
    '@blue-color',
    '@magenta-color',
    '@red-color',
    '@foreground-color'
]

const FORMATS = {
    datetime: '%b %-d, %Y, %H:%M:%S',
    millisecond: '%H:%M:%S.%f',
    second: '%H:%M:%S',
    minute: '%H:%M',
    hour: '%H:%M',
    day: '%b %-d',
    week: '%b %-d',
    month: '%b %Y',
    quarter: '%b %Y',
    year: '%Y'
}

/* Use custom date/time formatter */
ChartJS._adapters._date.override({

    formats() {
        return FORMATS
    },

    format(time, fmt) {
        return DateUtils.formatPercent(new Date(time), fmt)
    }

})


$.widget('qtoggle.basechart', $.qui.basewidget, {

    options: {
        title: null,
        legend: null,
        showTooltips: false,
        colors: DEFAULT_COLORS,
        labels: null,
        categories: null,
        unitOfMeasurement: null,
        panZoomMode: null,
        panZoomXMin: null,
        panZoomXMax: null,
        panZoomYMin: null,
        panZoomYMax: null,
        scalingFactor: 1,
        aspectRatio: 2,
        onPanZoomStart: function (xMin, xMax, yMin, yMax) {},
        onPanZoomEnd: function (xMin, xMax, yMin, yMax) {}
    },

    type: 'override-me',

    _create: function () {
        this._initChartJS()

        this.element.addClass(`qtoggle-chart-container qtoggle-${this.type}-chart-container`)

        if (this.options.disabled) {
            this.element.addClass('disabled')
        }
        else {
            this.element.attr('tabIndex', 0) /* Make element focusable */
        }

        this._scalingFactor = Window.getScalingFactor() * this.options.scalingFactor

        /* We need to compensate the global scaling factor, if any; the chart looks blurry otherwise. */
        if (Window.getScalingFactor() !== 1) {
            let compZoom = 100 / Window.getScalingFactor()
            this.element.css('zoom', `${compZoom}%`)
        }

        this._canvas = $('<canvas></canvas>', {class: 'qtoggle-chart'})
        this._canvasContext = this._canvas[0].getContext('2d')
        this.element.append(this._canvas)

        /* Temporarily add the chart element to DOM - it seems Chart.js needs this */
        Window.$body.append(this.element)

        this._data = {}
        this._chart = new ChartJS.Chart(this._canvasContext, {
            type: this.type,
            data: {},
            options: this._prepareOptions(this._getEnvironment())
        })

        this.element.remove()

        /* Register a double-tap event to reset zoom */
        if (this._chart._mc) {
            this._chart._mc.add(new Hammer.Tap({
                event: 'doubletap',
                taps: 2
            }))

            this._chart._mc.on('doubletap', function (e) {
                this._chart.resetZoom()
            }.bind(this))
        }

        this._panning = false
        this._zooming = false
    },

    _initChartJS: function () {
        if (!ChartJS.Chart._qToggleInitialized) {
            ChartJS.Chart.register(
                ChartJS.LineController,
                ChartJS.BarController,
                ChartJS.DoughnutController,
                ChartJS.LineElement,
                ChartJS.BarElement,
                ChartJS.PointElement,
                ChartJS.ArcElement,
                ChartJS.LinearScale,
                ChartJS.CategoryScale,
                ChartJS.TimeScale,
                ChartJS.Legend,
                ChartJS.Title,
                ChartJS.Tooltip,
                ChartJS.Filler
            )

            ChartJS.Chart._qToggleInitialized = true
        }
    },

    getValue: function () {
        return this._data
    },

    setValue: function (value) {
        this._data = value
        this._chart.data = this._prepareData(this._data)
        this._chart.update()
    },

    getXRange: function () {
        return {
            min: this._chart.scales['x'].min,
            max: this._chart.scales['x'].max
        }
    },

    setXRange: function (xMin, xMax) {
        this._chart.scales['x'].options.min = xMin
        this._chart.scales['x'].options.max = xMax
    },

    getYRange: function () {
        return {
            min: this._chart.scales['y'].min,
            max: this._chart.scales['y'].max
        }
    },

    setYRange: function (yMin, yMax) {
        this._chart.scales['y'].options.min = yMin
        this._chart.scales['y'].options.max = yMax
        this._chart.update()
    },

    _getEnvironment: function () {
        let em2px = CSS.em2px(this._scalingFactor)

        return {
            foregroundColor: Theme.getColor('@foreground-color'),
            backgroundColor: Theme.getColor('@background-color'),
            backgroundRootColor: Theme.getColor('@background-root-color'),
            foregroundActiveColor: Theme.getColor('@foreground-active-color'),
            borderColor: Theme.getColor('@border-color'),
            fontFamily: Theme.getVar('base-font-family'),
            em2px: em2px,
            px1: em2px * 0.0625,
            px2: em2px * 0.125,
            px3: em2px * 0.1875,
            px4: em2px * 0.25
        }
    },

    _getColors: function () {
        return this.options.colors.map(Theme.getColor)
    },

    _prepareOptions: function (environment) {
        return {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: this.options.aspectRatio,
            spanGaps: true,
            animation: {
                duration: 0
            },
            hover: this._makeHoverOptions(environment),
            scales: this._makeScalesOptions(environment),
            plugins: this._makePluginsOptions(environment),
            elements: this._makeElementsOptions(environment)
        }
    },

    _prepareData: function (data) {
        let labels = this.options.labels
        if (!labels) {
            labels = this.options.colors.map(() => '')
        }

        let datasets = this._adaptDatasets(data, this._getEnvironment(), this._getColors())
        datasets.forEach(function (ds, i) {
            ObjectUtils.setDefault(ds, 'label', labels[i])
        })

        return {
            labels: this.options.categories,
            datasets: datasets
        }
    },

    _adaptDatasets: function (data, environment, colors) {
        return data
    },

    _makeHoverOptions: function (environment) {
        return {
            mode: 'nearest',
            intersect: true
        }
    },

    _makeTitleOptions: function (environment) {
        return {
            display: this.options.title != null,
            font: this._makeFontOptions(environment),
            text: this.options.title
        }
    },

    _makeLegendOptions: function (environment) {
        return {
            display: this.options.legend != null,
            position: this.options.legend,
            labels: {
                font: this._makeFontOptions(environment),
                padding: environment.em2px * 0.5,
                usePointStyle: true,
                boxWidth: environment.px4,
                generateLabels: function (chart) {
                    /* Hack to force fill color to be the same as stroke (border) color */
                    let labels = ChartJS.Chart.defaults.plugins.legend.labels.generateLabels(chart)
                    labels.forEach(function (label) {
                        label.fillStyle = label.strokeStyle
                    })

                    return labels
                }
            }
        }
    },

    _makeScalesOptions: function (environment) {
        return {}
    },

    _makeGridLinesOptions: function (environment) {
        return {
            color: environment.borderColor,
            lineWidth: environment.px1
        }
    },

    _makeTicksOptions: function (environment, scaleName) {
        return {
            color: environment.foregroundActiveColor,
            font: ObjectUtils.combine(this._makeFontOptions(environment), {
                size: environment.em2px * 0.75
            }),
            callback: scaleName === 'y' ? function (value, index, values) { /* Show units on vertical axis */
                return `${value}${this.options.unitOfMeasurement || ''}`
            }.bind(this) : null
        }
    },

    _makeTooltipOptions: function (environment) {
        let colors = this._getColors()

        return {
            enabled: this.options.showTooltips,
            mode: 'index',
            intersect: true,
            animation: {
                duration: 50
            },
            backgroundColor: Colors.alpha(environment.backgroundRootColor, 0.9),
            borderColor: environment.foregroundColor,
            borderWidth: environment.px1 / 2, /* No idea why this actually results in a 1px border */
            usePointStyle: true,
            boxWidth: environment.em2px * 0.4,
            boxHeight: environment.em2px * 0.4,
            titleFont: ObjectUtils.combine(this._makeFontOptions(environment), {
                size: environment.em2px * 0.8
            }),
            bodyFont: ObjectUtils.combine(this._makeFontOptions(environment), {
                size: environment.em2px * 0.8
            }),
            titleColor: environment.foregroundColor,
            bodyColor: environment.foregroundColor,
            callbacks: {
                labelColor: function (context) {
                    /* Hack to force fill color to be the same as stroke (border) color */
                    return {
                        borderColor: environment.foregroundColor,
                        backgroundColor: colors[context.datasetIndex % colors.length]
                    }
                },
                label: function (context) {
                    return ` ${context.dataPoint.y}${this.options.unitOfMeasurement || ''}`
                }.bind(this)
            }
        }
    },

    _makePluginsOptions: function (environment) {
        let plugins = {
            title: this._makeTitleOptions(environment),
            legend: this._makeLegendOptions(environment),
            tooltip: this._makeTooltipOptions(environment)
        }

        if (this.options.panZoomMode) {
            plugins.zoom = this._makeZoomPluginOptions(environment)
        }

        return plugins
    },

    _makeElementsOptions: function (environment) {
        return {
            point: {
                hitRadius: environment.em2px / 2
            }
        }
    },

    _makeZoomPluginOptions: function (environment) {
        return {
            pan: {
                enabled: true,
                mode: this.options.panZoomMode,
                speed: 0.1,
                rangeMin: {
                    x: this.options.panZoomXMin != null ? this.options.panZoomXMin : undefined,
                    y: this.options.panZoomYMin != null ? this.options.panZoomYMin : undefined
                },
                rangeMax: {
                    x: this.options.panZoomXMax != null ? this.options.panZoomXMax : undefined,
                    y: this.options.panZoomYMax != null ? this.options.panZoomYMax : undefined
                },
                onPan: function () {
                    if (!this._panning) {
                        this._panning = true
                        if (!this._zooming) {
                            this._handlePanZoomStart()
                        }
                    }
                }.bind(this),
                onPanComplete: function () {
                    if (!this._zooming && this._panning) {
                        this._handlePanZoomEnd()
                    }
                    this._panning = false
                }.bind(this)
            },
            zoom: {
                enabled: true,
                mode: this.options.panZoomMode,
                speed: 0.2,
                rangeMax: {
                    x: this.options.panZoomXMax != null ? this.options.panZoomXMax : undefined,
                    y: this.options.panZoomYMax != null ? this.options.panZoomYMax : undefined
                },
                onZoom: function () {
                    if (!this._zooming) {
                        this._zooming = true
                        if (!this._panning) {
                            this._handlePanZoomStart()
                        }
                    }
                }.bind(this),
                onZoomComplete: function () {
                    if (!this._panning && this._zooming) {
                        this._handlePanZoomEnd()
                    }
                    this._zooming = false
                }.bind(this)
            }
        }
    },

    _makeFontOptions: function (environment) {
        return {
            family: environment.fontFamily,
            style: 'normal',
            size: environment.em2px
        }
    },

    _handlePanZoomStart: function () {
        let xMin = this._chart.scales['x'].min
        let xMax = this._chart.scales['x'].max
        let yMin = this._chart.scales['y'].min
        let yMax = this._chart.scales['y'].max

        this.options.onPanZoomStart(xMin, xMax, yMin, yMax)
    },

    _handlePanZoomEnd: function () {
        let xMin = this._chart.scales['x'].min
        let xMax = this._chart.scales['x'].max
        let yMin = this._chart.scales['y'].min
        let yMax = this._chart.scales['y'].max

        this.options.onPanZoomEnd(xMin, xMax, yMin, yMax)
    },

    _setOption: function (key, value) {
        this._super(key, value)

        switch (key) {
            case 'disabled':
                this.element.toggleClass('disabled', value)
                if (value) {
                    this.element.removeAttr('tabIndex')
                }
                else {
                    this.element.attr('tabIndex', 0)
                }
                break
        }

        /* Preserve scale ranges */
        let scaleRanges = ObjectUtils.mapValue(this._chart.scales, scale => ({
            min: scale.options.min,
            max: scale.options.max
        }))
        let options = this._prepareOptions(this._getEnvironment())

        this._chart.data = this._prepareData(this._data)
        ObjectUtils.forEach(scaleRanges, function (scaleName, {min, max}) {
            let scale = options.scales[scaleName]
            if (!scale) {
                return
            }

            if (min != null && max != null) {
                scale.min = min
                scale.max = max
            }
        })

        this._chart.options = options
        this._chart.update()
    }

})

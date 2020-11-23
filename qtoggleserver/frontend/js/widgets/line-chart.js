
import $ from '$qui/lib/jquery.module.js'

import * as ArrayUtils  from '$qui/utils/array.js'
import * as Colors      from '$qui/utils/colors.js'
import * as ObjectUtils from '$qui/utils/object.js'

import './base-chart.js'


const SHOW_POINTS_AUTO_VISIBLE_MAX = 200


$.widget('qtoggle.linechart', $.qtoggle.basechart, {
    /* Expected format for value is one of:
     *  * [y0, y1, ...]
     *  * [[x0, y0a, y0b, ...], [x1, y1a, y1b, ...], ...]
     *  * [[[x0a, y0a], [x1a, y1a], ...], [[x0b, y0b], [x1b, y1b], ...], ...] */

    options: {
        xMin: null,
        xMax: null,
        yMin: null,
        yMax: null,
        showPoints: null, /* null = auto */
        showMajorTicks: false,
        allowTickRotation: false,
        xTicksStepSize: null,
        yTicksStepSize: null,
        xTicksLabelCallback: null,
        yTicksLabelCallback: null,
        smooth: true,
        fillArea: true,
        stepped: false
    },

    type: 'line',

    _create: function () {
        this._super()

        this._pointRadius = null
    },

    _makeScalesOptions: function (environment) {
        /* min/max values must be supplied as undefined if not specified */
        let xMin = this.options.xMin == null ? undefined : this.options.xMin
        let xMax = this.options.xMax == null ? undefined : this.options.xMax
        let yMin = this.options.yMin == null ? undefined : this.options.yMin
        let yMax = this.options.yMax == null ? undefined : this.options.yMax

        return ObjectUtils.combine(this._super(environment), {
            x: {
                type: 'linear',
                min: xMin,
                max: xMax,
                gridLines: this._makeGridLinesOptions(environment),
                ticks: this._makeTicksOptions(environment, 'x')
            },
            y: {
                type: 'linear',
                min: yMin,
                max: yMax,
                gridLines: this._makeGridLinesOptions(environment),
                ticks: this._makeTicksOptions(environment, 'y')
            }
        })
    },

    _makeTicksOptions: function (environment, scaleName) {
        let options = this._super(environment, scaleName)

        // eslint-disable-next-line no-undef-init
        let stepSize = undefined
        // eslint-disable-next-line no-undef-init
        let labelCallback = undefined
        if (scaleName === 'x') {
            if (this.options.xTicksStepSize != null) {
                stepSize = this.options.xTicksStepSize
            }
            if (this.options.xTicksLabelCallback) {
                labelCallback = this.options.xTicksLabelCallback
            }
        }
        else if (scaleName === 'y') {
            if (this.options.yTicksStepSize != null) {
                stepSize = this.options.yTicksStepSize
            }
            if (this.options.yTicksLabelCallback) {
                labelCallback = this.options.yTicksLabelCallback
            }
            else {
                labelCallback = function (value, index, values) { /* Show units on vertical axis, by default */
                    return `${value}${this.options.unitOfMeasurement || ''}`
                }.bind(this)
            }
        }

        return ObjectUtils.combine(options, {
            autoSkip: false,
            autoSkipPadding: environment.em2px / 2,
            maxRotation: this.options.allowTickRotation ? null : 0,
            stepSize: stepSize,
            major: {
                enabled: this.options.showMajorTicks
            },
            font: function (context) {
                return ObjectUtils.combine(options.font, {
                    style: context.tick && context.tick.major ? 'bold' : 'normal'
                })
            },
            callback: labelCallback
        })
    },

    _makeElementsOptions: function (environment) {
        return ObjectUtils.combine(this._super(environment), {
            line: {
                tension: this.options.smooth ? 0.4 : 0,
                borderDash: []
            }
        })
    },

    _adaptDatasets: function (data, environment, colors) {
        if (!Array.isArray(data) || data.length === 0) {
            return []
        }

        /* Normalize [y0, y1, ...] -> [[0, y0], [1, y1], ...] */
        if (!Array.isArray(data[0])) {
            data = data.map((v, i) => [i, v])
        }

        if (data[0].length === 0) {
            return []
        }

        /* Normalize [[x0, y0a, y0b, ...], [x1, y1a, y1b, ...], ...] ->
         *           [[[x0, y0a], [x1, y1a], ...], [[x0, y0b], [x1, y1b], ...], ...] */
        if (!Array.isArray(data[0][0])) {
            /* The data is assumed to be a list of multidimensional points.
             * The first point is used to determine the number of datasets; its first dimension is the x axis. */

            let datasetCount = data[0].length - 1
            data = ArrayUtils.range(0, datasetCount).map(function (i) {
                return data.map(p => [p[0], p[i + 1]])
            })
        }

        /* Map input data to axes & adapt datasets */
        return data.map(function (dataset, i) {
            let color = colors[i % colors.length]
            return {
                borderColor: color,
                borderCapStyle: 'round',
                borderJoinStyle: 'round',
                hoverBorderColor: color,
                hoverBackgroundColor: color,
                backgroundColor: environment.backgroundColor,
                borderWidth: environment.px2,
                pointStyle: 'circle',
                pointBorderWidth: environment.px1,
                pointHoverBorderWidth: environment.px1,
                pointRadius: this._getPointRadius.bind(this, environment),
                pointHoverRadius: this.options.showPoints !== false ? environment.px3 : 0,
                stepped: this.options.stepped,
                fill: this.options.fillArea ? {
                    target: 'origin',
                    above: Colors.alpha(color, 0.2),
                    below: Colors.alpha(color, 0.2)
                } : null,
                data: dataset.map(pair => ({x: pair[0], y: pair[1]}))
            }
        }.bind(this))
    },

    _handlePanZoomStart() {
        this._super()

        /* Invalidate point radius */
        this._pointRadius = null
    },

    _getPointRadius(environment, context) {
        if (this.options.showPoints === false) {
            return 0
        }
        if (this.options.showPoints === true) {
            return environment.px3
        }
        if (this._pointRadius != null) {
            return this._pointRadius
        }

        let scaleX = context.chart.scales['x']
        let scaleY = context.chart.scales['y']
        let data = context.dataset.data

        let visibleXCount = 0
        let visibleYCount = 0
        for (let i = 0; i < data.length; i++) {
            let point = data[i]
            if (scaleX.min <= point.x && scaleX.max >= point.x) {
                visibleXCount++
            }
            if (scaleY.min <= point.y && scaleY.max >= point.y) {
                visibleYCount++
            }
            if (visibleXCount > SHOW_POINTS_AUTO_VISIBLE_MAX && visibleYCount > SHOW_POINTS_AUTO_VISIBLE_MAX) {
                return (this._pointRadius = 0)
            }
        }

        return (this._pointRadius = environment.px3)
    },

    _setOption: function (key, value) {
        switch (key) {
            case 'showPoints':
                this._pointRadius = null
                break
        }

        this._super(key, value)
    }

})

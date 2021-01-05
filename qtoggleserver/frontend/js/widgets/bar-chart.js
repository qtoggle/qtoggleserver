
import $ from '$qui/lib/jquery.module.js'

import * as Colors      from '$qui/utils/colors.js'
import * as ObjectUtils from '$qui/utils/object.js'

import './base-chart.js'


$.widget('qtoggle.barchart', $.qtoggle.basechart, {
    /* Expected format for value is one of:
     *  * [v0, v1, ...]
     *  * [[v0a, v1a, ...], [v0b, v1b, ...], ...]
     */

    options: {
        yMin: null,
        yMax: null,
        yTicksStepSize: null,
        yTicksLabelCallback: null,
        allowTickRotation: false,
        stacked: false
    },

    type: 'bar',

    _makeScalesOptions: function (environment) {
        return ObjectUtils.combine(this._super(environment), {
            x: {
                type: 'category',
                gridLines: this._makeGridLinesOptions(environment),
                ticks: this._makeTicksOptions(environment, 'x'),
                stacked: this.options.stacked
            },
            y: {
                type: 'linear',
                min: this.options.yMin,
                max: this.options.yMax,
                gridLines: this._makeGridLinesOptions(environment),
                ticks: this._makeTicksOptions(environment, 'y'),
                stacked: this.options.stacked
            }
        })
    },

    _makeTicksOptions: function (environment, scaleName) {
        let options = ObjectUtils.combine(this._super(environment, scaleName), {
            autoSkip: false,
            autoSkipPadding: environment.em2px / 2,
            maxRotation: this.options.allowTickRotation ? 90 : 0
        })

        if (scaleName === 'y') {
            if (this.options.yTicksStepSize != null) {
                options.stepSize = this.options.yTicksStepSize
            }
            if (this.options.yTicksLabelCallback) {
                options.callback = this.options.yTicksLabelCallback
            }
            else {
                options.callback = function (value, index, values) { /* Show units on vertical axis, by default */
                    return `${value}${this.options.unitOfMeasurement || ''}`
                }.bind(this)
            }
        }

        return options
    },

    _makeTooltipOptions: function (environment) {
        return ObjectUtils.combine(this._super(environment), {
            mode: 'nearest'
        })
    },

    _adaptDatasets: function (data, environment, colors) {
        if (!Array.isArray(data) || data.length === 0) {
            return []
        }

        /* Normalize [v0, v1, ...] -> [[v0, v1, ...]] */
        if (!Array.isArray(data[0])) {
            data = [data]
        }

        if (data[0].length === 0) {
            return []
        }

        /* Map input data to axes & adapt datasets */
        return data.map(function (dataset, i) {
            let color = colors[i % colors.length]
            return {
                hoverBackgroundColor: Colors.alpha(color, 0.75),
                backgroundColor: color,
                borderColor: color,
                borderWidth: 0,
                data: dataset.map((v, j) => ({x: j, y: v}))
            }
        })
    }

})

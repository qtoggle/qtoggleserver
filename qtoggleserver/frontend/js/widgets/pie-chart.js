
import $ from '$qui/lib/jquery.module.js'

import * as Colors      from '$qui/utils/colors.js'
import * as ObjectUtils from '$qui/utils/object.js'

import './base-chart.js'


$.widget('qtoggle.piechart', $.qtoggle.basechart, {
    /* Expected format for value is one of:
     *  * [v0, v1, ...]
     */

    options: {
    },

    type: 'doughnut',

    _makeTooltipOptions: function (environment) {
        return ObjectUtils.combine(this._super(environment), {
            callbacks: {
                labelColor: function (context) {
                    /* Hack to force fill color to be the same as stroke (border) color */
                    return {
                        borderColor: environment.foregroundColor,
                        backgroundColor: context.element.options.backgroundColor
                    }
                },
                label: function (context) {
                    return ` ${context.dataPoint}${this.options.unitOfMeasurement || ''}`
                }.bind(this)
            }
        })
    },

    _adaptDatasets: function (data, environment, colors) {
        if (!Array.isArray(data) || data.length === 0) {
            return []
        }

        return [{
            backgroundColor: colors,
            hoverBackgroundColor: colors.map(c => Colors.alpha(c, 0.75)),
            borderColor: environment.backgroundColor,
            hoverBorderColor: environment.backgroundColor,
            borderWidth: environment.px2,
            data: data
        }]
    }

})

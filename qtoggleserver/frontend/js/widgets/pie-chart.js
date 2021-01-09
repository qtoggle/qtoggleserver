
import $ from '$qui/lib/jquery.module.js'

import * as Colors      from '$qui/utils/colors.js'
import * as ObjectUtils from '$qui/utils/object.js'

import * as ChartJS from '$app/lib/chartjs.module.js'

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

    _makeLegendOptions: function (environment) {
        let options = this._super(environment)
        let labels = this.options.labels
        let unit = this.options.unitOfMeasurement

        options.labels.generateLabels = function (chart) {
            if (!labels || labels.length < 2) {
                return []
            }

            /* Pie chart extracts all legend labels from the one single data set */
            chart.data.labels = labels
            let generatedLabels = ChartJS.DoughnutController.defaults.plugins.legend.labels.generateLabels(chart)

            /* Calculate values and percents */
            let values = chart.data.datasets[0].data
            let valuesSum = values.reduce((a, v) => a + v, 0)
            let valuesStr = values.map(v => `${v}${unit}`)
            let percents = values.map(v => v * 100 / valuesSum)
            let percentsStr = percents.map(p => `${Math.round(p * 10) / 10}%`)

            /* Duplicate each legend label so that we can show additional details, such as actual value and percent */
            let duplicatedLabels = []
            generatedLabels.forEach(function (label, i) {

                let dupLabel = ObjectUtils.copy(label, /* deep = */ true)
                dupLabel.pointStyle = 'dash'
                dupLabel.lineWidth = 0
                dupLabel.text = `${valuesStr[i]} | ${percentsStr[i]}`

                duplicatedLabels.push(label)
                duplicatedLabels.push(dupLabel)

            })

            return duplicatedLabels
        }

        return options
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

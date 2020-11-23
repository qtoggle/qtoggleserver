
import $ from '$qui/lib/jquery.module.js'

import './line-chart.js'


$.widget('qtoggle.timechart', $.qtoggle.linechart, {
    /* Expected format for value is one of:
     *  * [[t0, y0a, y0b, ...], [t1, y1a, y1b, ...], ...]
     *  * [[[t0a, y0a], [t1a, y1a], ...], [[t0b, y0b], [t1b, y1b], ...], ...]
     *
     * Time values must be given as Unix timestamps in milliseconds.
     */

    options: {
        unit: null
    },

    _makeScalesOptions: function (environment) {
        let options = this._super(environment)

        options.x.type = 'time'
        options.x.time = {
            unit: this.options.unit ? this.options.unit : undefined
        }

        return options
    }

})

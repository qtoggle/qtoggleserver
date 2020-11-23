
import * as PortsAPI from '$app/api/ports.js'


/**
 * @alias qtoggle.common.HistoryDownloadTooManyRequests
 * @extends Error
 */
export class HistoryDownloadTooManyRequests extends Error {
}


class Interval {

    constructor(from, to, samples) {
        this.from = from
        this.to = to
        this.samples = samples
    }

    isVoid() {
        return this.from >= this.to
    }

    getSlice(from, to) {
        if (this.to <= from) {
            return null
        }
        if (this.from >= to) {
            return null
        }
        if (from < this.to && this.to <= to) {
            if (from <= this.from && this.from < to) {
                /* This is included in range */
                return this
            }
            else {
                /* The right side of this overlaps with the left side of the range */
                return new Interval(from, this.to, this.getSliceSamples(from, this.to))
            }
        }
        else {
            if (this.from <= from && from < this.to) {
                /* Range is included in this */
                return new Interval(from, to, this.getSliceSamples(from, to))
            }
            else {
                /* The right side of range overlaps with the left side of this */
                return new Interval(this.from, to, this.getSliceSamples(this.from, to))
            }
        }
    }

    tryMerge(interval) {
        if (this.from < interval.to && this.to >= interval.from) {
            let samples
            if (this.to === interval.from) {
                samples = this.samples.concat(interval.samples)
            }
            else {
                if (interval.samples.length > 0) {
                    samples = this.samples.filter(s => s.timestamp < interval.samples[0].timestamp)
                    samples = samples.concat(interval.samples)
                }
                else {
                    samples = this.samples
                }
            }
            return new Interval(this.from, interval.to, samples)
        }
        else if (interval.from < this.to && interval.to >= this.from) {
            let samples
            if (interval.to === this.from) {
                samples = interval.samples.concat(this.samples)
            }
            else {
                if (this.samples.length > 0) {
                    samples = interval.samples.filter(s => s.timestamp < this.samples[0].timestamp)
                    samples = samples.concat(this.samples)
                }
                else {
                    samples = interval.samples
                }
            }

            return new Interval(interval.from, this.to, samples)
        }

        return null /* No merging possible */
    }

    getSliceSamples(from, to) {
        if (this.samples.length === 0) {
            return []
        }

        let slice = []
        let i = 0
        while (i < this.samples.length && this.samples[i].timestamp < from) {
            i++
        }
        while (i < this.samples.length && this.samples[i].timestamp < to) {
            slice.push(this.samples[i++])
        }

        return slice
    }

}


/**
 * @alias qtoggle.common.HistoryDownloadManager
 */
class HistoryDownloadManager {

    /**
     * @constructs
     * @param {Object} port
     */
    constructor(port) {
        this._port = port
        this._intervals = []
        this._requestCount = 0
        this._maxRequests = 0
    }

    /**
     * @param {Number} from
     * @param {Number} to
     * @param {Number} [maxRequests]
     * @return {Promise<Object[]>}
     */
    fetch(from, to, maxRequests = 0) {
        let gaps = this._findGaps(from, to)

        this._requestCount = 0
        this._maxRequests = maxRequests

        /* Chain API requests for all missing intervals */
        let promise = Promise.resolve()
        gaps.forEach(function (gap) {
            promise = promise.then(function () {
                return this._downloadAndCache(gap)
            }.bind(this))
        }.bind(this))

        return promise.then(function () {
            return this._getCachedSamples(from, to)
        }.bind(this))
    }

    _downloadAndCache({from, to}) {
        return this._download({from, to}).then(function (samples) {

            /* At this point, we can be sure we've got all existing samples for the requested gap */
            this._addInterval(new Interval(from, to, samples))

        }.bind(this))
    }

    _download({from, to}) {
        if (this._maxRequests > 0 && this._requestCount >= this._maxRequests) {
            return Promise.reject(new HistoryDownloadTooManyRequests())
        }
        this._requestCount++

        let downloadPromise = PortsAPI.getPortHistory(this._port.id, from, to, PortsAPI.HISTORY_MAX_LIMIT)

        return downloadPromise.then(function (samples) {

            if (samples.length >= PortsAPI.HISTORY_MAX_LIMIT) {
                /* If we were given a number of samples equal to the download limit, it's very likely that there's
                 * more to be downloaded. */
                let lastSample = samples[samples.length - 1]
                return this._download({from: lastSample.timestamp, to}).then(function (newSamples) {
                    return samples.concat(newSamples)
                })
            }
            else {
                return samples
            }

        }.bind(this))
    }

    _addInterval(interval) {
        if (this._intervals.length === 0) {
            this._intervals.push(interval)
            return
        }

        /* Find correct position for interval */
        let pos = 0
        while (pos < this._intervals.length && this._intervals[pos].from < interval.from) {
            pos++
        }

        if (pos === 0) {
            let merged = this._intervals[0].tryMerge(interval)
            if (merged) {
                this._intervals[0] = merged
            }
            else {
                this._intervals.splice(0, 0, interval)
            }
        }
        else if (pos === this._intervals.length) {
            let merged = this._intervals[this._intervals.length - 1].tryMerge(interval)
            if (merged) {
                this._intervals[this._intervals.length - 1] = merged
            }
            else {
                this._intervals.push(interval)
            }
        }
        else {
            let merged = this._intervals[pos - 1].tryMerge(interval) /* Try to merge with previous interval */
            if (merged) {
                this._intervals[pos - 1] = merged
            }
            else {
                merged = this._intervals[pos].tryMerge(interval) /* Try to merge with next interval */
                if (merged) {
                    this._intervals[pos] = merged
                }
                else {
                    this._intervals.splice(pos, 0, interval)
                }
            }

            /* Our new interval might have just bridged the gap between pos - 1 and pos */
            if (merged) {
                merged = this._intervals[pos - 1].tryMerge(this._intervals[pos])
                if (merged) {
                    this._intervals[pos - 1] = merged
                    this._intervals.splice(pos, 1)
                }
            }
        }
    }

    _findGaps(from, to) {
        if (this._intervals.length === 0) {
            return [{from, to}]
        }

        if (to <= this._intervals[0].from || from >= this._intervals[this._intervals.length - 1].to) {
            /* Completely before the first interval or after the last one */
            return [{from, to}]
        }

        let startPos = 0
        while (startPos < this._intervals.length && this._intervals[startPos].from < from) {
            startPos++
        }

        let stopPos = startPos
        while (stopPos < this._intervals.length && this._intervals[stopPos].to < to) {
            stopPos++
        }

        let gaps = []
        if (startPos < this._intervals.length) {
            if (from < this._intervals[startPos].from) {
                gaps.push({from, to: this._intervals[startPos].from})
            }
            for (let pos = startPos; pos < stopPos - 1; pos++) {
                gaps.push({from: this._intervals[pos].to, to: this._intervals[pos + 1].from})
            }
        }

        return gaps
    }

    _getCachedSamples(from, to) {
        /* Find all cached intervals intersections */
        let intervals = this._intervals.map(i => i.getSlice(from, to)).filter(i => i != null)

        /* Extract and merge samples */
        return intervals.reduce((s, i) => s.concat(i.samples), [])
    }

}


export default HistoryDownloadManager

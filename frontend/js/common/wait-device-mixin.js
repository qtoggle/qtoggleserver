
import ConditionVariable from '$qui/base/condition-variable.js'
import {AssertionError}  from '$qui/base/errors.js'
import {Mixin}           from '$qui/base/mixwith.js'
import ViewMixin         from '$qui/views/view.js'


const __FIX_JSDOC = null /* without this, JSDoc considers following symbol undocumented */


/** @lends qtoggle.common.WaitDeviceMixin */
const WaitDeviceMixin = Mixin((superclass = Object) => {

    /**
     * A mixin to be used with objects that wait for a device to go offline and/or come back online.
     * @alias qtoggle.common.WaitDeviceMixin
     * @mixin
     */
    class WaitDeviceMixin extends superclass {

        /**
         * @constructs
         * @param {...*} args
         */
        constructor({...args} = {}) {
            super(args)

            this._whenDeviceOnline = null
            this._whenDeviceOffline = null
        }

        /**
         * Return a condition variable that resolves when device comes online.
         * @returns {qui.base.ConditionVariable}
         */
        waitDeviceOnline() {
            if (this._whenDeviceOnline || this._whenDeviceOffline) {
                throw new AssertionError('Attempt to wait for device to come online while already waiting')
            }

            return (this._whenDeviceOnline = new ConditionVariable())
        }

        /**
         * Tell if we're currently waiting for device to come online.
         * @returns {Boolean}
         */
        isWaitingDeviceOnline() {
            return !!this._whenDeviceOnline
        }

        /**
         * Return a condition variable that resolves when device goes offline.
         * @returns {qui.base.ConditionVariable}
         */
        waitDeviceOffline() {
            if (this._whenDeviceOnline || this._whenDeviceOffline) {
                throw new AssertionError('Attempt to wait for device to go offline while already waiting')
            }

            return (this._whenDeviceOffline = new ConditionVariable())
        }

        /**
         * Tell if we're currently waiting for device to go offline.
         * @returns {Boolean}
         */
        isWaitingDeviceOffline() {
            return !!this._whenDeviceOffline
        }

        /**
         * Fulfill the device online condition.
         */
        fulfillDeviceOnline() {
            if (!this._whenDeviceOnline) {
                throw new AssertionError('Attempt to fulfill device online but not waiting')
            }

            this._whenDeviceOnline.fulfill()
            this._whenDeviceOnline = null
        }

        /**
         * Fulfill the device offline condition.
         */
        fulfillDeviceOffline() {
            if (!this._whenDeviceOffline) {
                throw new AssertionError('Attempt to fulfill device offline but not waiting')
            }

            this._whenDeviceOffline.fulfill()
            this._whenDeviceOffline = null
        }

        /**
         * Cancel waiting for device to come online or go offline.
         */
        cancelWaiting() {
            if (this._whenDeviceOnline) {
                this._whenDeviceOnline.cancel()
                this._whenDeviceOnline = null
            }

            if (this._whenDeviceOffline) {
                this._whenDeviceOffline.cancel()
                this._whenDeviceOffline = null
            }

            if (this instanceof ViewMixin && this.inProgress()) {
                this.clearProgress()
            }
        }

    }

    return WaitDeviceMixin

})


export default WaitDeviceMixin

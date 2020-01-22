
import ConditionVariable from '$qui/base/condition-variable.js'
import {AssertionError}  from '$qui/base/errors.js'
import {Mixin}           from '$qui/base/mixwith.js'


const WaitDeviceMixin = Mixin((superclass = Object) => {

    class WaitDeviceMixin extends superclass {

        constructor({...params} = {}) {
            super(params)

            this._whenDeviceOnline = null
            this._whenDeviceOffline = null
        }

        waitDeviceOnline() {
            if (this._whenDeviceOnline || this._whenDeviceOffline) {
                throw new AssertionError('Attempt to wait for device to come online while already waiting')
            }

            return (this._whenDeviceOnline = new ConditionVariable())
        }

        isWaitingDeviceOnline() {
            return !!this._whenDeviceOnline
        }

        isWaitingDeviceOffline() {
            return !!this._whenDeviceOffline
        }

        waitDeviceOffline() {
            if (this._whenDeviceOnline || this._whenDeviceOffline) {
                throw new AssertionError('Attempt to wait for device to go offline while already waiting')
            }

            return (this._whenDeviceOffline = new ConditionVariable())
        }

        fulfillDeviceOnline() {
            if (!this._whenDeviceOnline) {
                throw new AssertionError('Attempt to fulfill device online but not waiting')
            }

            this._whenDeviceOnline.fulfill()
            this._whenDeviceOnline = null
        }

        fulfillDeviceOffline() {
            if (!this._whenDeviceOffline) {
                throw new AssertionError('Attempt to fulfill device offline but not waiting')
            }

            this._whenDeviceOffline.fulfill()
            this._whenDeviceOffline = null
        }

        cancelWaitingDeviceOnline() {
            if (!this._whenDeviceOnline) {
                throw new AssertionError('Attempt to cancel waiting for device to come online while not waiting')
            }

            this.clearProgress()
            this._whenDeviceOnline.cancel()
            this._whenDeviceOnline = null
        }

        cancelWaitingDevice() {
            if (this._whenDeviceOnline) {
                this._whenDeviceOnline.cancel()
                this._whenDeviceOnline = null
            }

            if (this._whenDeviceOffline) {
                this._whenDeviceOffline.cancel()
                this._whenDeviceOffline = null
            }
        }

    }

    return WaitDeviceMixin

})


export default WaitDeviceMixin

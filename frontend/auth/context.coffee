import h from 'react-hyperscript'
import {APIContext, StatefulComponent} from '@macrostrat/ui-components'
import {createContext} from 'react'

AuthContext = createContext({})

class AuthProvider extends StatefulComponent
  @contextType: APIContext
  constructor: (props)->
    super props
    @state = {
      login: false
      username: null
      isLoggingIn: false
      invalidAttempt: false
    }

  componentDidMount: ->
    @getStatus()

  getStatus: =>
    {get} = @context
    {login, username} = await get '/auth/status'
    @setState {login, username}

  requestLoginForm: (v)=>
    console.log "Requesting login form"
    v ?= true
    @setState {isLoggingIn: v}

  doLogin: (data)=>
    {post} = @context
    {login, username} = await post '/auth/login', data
    invalidAttempt = false
    isLoggingIn = false
    if not login
      invalidAttempt = true
      isLoggingIn = true
    @setState {
      login,
      username,
      isLoggingIn
      invalidAttempt
    }

  doLogout: =>
    {post} = @context
    {login} = await post '/auth/logout'
    @setState {
      login,
      username: null,
      isLoggingIn: false
    }

  render: =>
    methods = do => {doLogin, doLogout, requestLoginForm} = @
    value = {methods..., @state...}
    h AuthContext.Provider, {value}, @props.children

export {AuthContext, AuthProvider}

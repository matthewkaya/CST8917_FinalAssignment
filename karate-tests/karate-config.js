function fn() {
  var config = {
    baseUrl: 'https://miniature-disco-x467wrg9gvxf6v6g-7071.app.github.dev/api'
  };

  // Perform login to get the token
  var loginResponse = karate.callSingle('classpath:Karate-tests/features/authentication.feature@login', config);
  config.authToken = 'Bearer ' + loginResponse.token;

  return config;
}
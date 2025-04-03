Feature: Authentication API Tests

  @login
  Scenario: User login
    Given path 'user/login'
    And request { "email": "mucteb@gmail.com", "password": "12345" }
    And header Content-Type = 'application/json'
    When method post
    Then status 200
    And match response.token != null
    * def token = response.token
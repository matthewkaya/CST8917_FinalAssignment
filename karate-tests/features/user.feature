Feature: User Management API Tests

  Background:
    * url baseUrl
    * header Authorization = authToken

  Scenario: Create a new user
    Given path 'user'
    And request { "firstName": "John", "lastName": "Doe", "email": "john.doe@example.com", "password": "password123", "phone": "1234567890" }
    And header Content-Type = 'application/json'
    When method post
    Then status 201
    And match response.message == 'User created successfully'

  Scenario: Get user details
    Given path 'user'
    When method get
    Then status 200
    And match response.email == 'john.doe@example.com'

  Scenario: Update user information
    Given path 'user'
    And request { "firstName": "Jane", "lastName": "Smith" }
    And header Content-Type = 'application/json'
    When method put
    Then status 200
    And match response.message == 'User updated successfully'

  Scenario: Delete a user
    Given path 'user'
    When method delete
    Then status 200
    And match response.message == 'User deleted successfully'
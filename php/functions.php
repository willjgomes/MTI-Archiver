<?php
/* Functions required to expose needed REST API functionality for WPG Books Post
 *
 * These must be added to the functions.php under the WordPress site's theme folder.
 * For the default test site the theme being used is:  Twenty Twenty-Five
*/

function enable_cpt_in_rest_api() {
    // Replace 'your_custom_post_type' with your actual custom post type slug
    $post_type = 'books'; 

    // Check if the custom post type exists and is not already exposed in REST
    if ( post_type_exists( $post_type ) ) {
        $args = array(
            'show_in_rest' => true,		// Enable REST API exposure
            'rest_base' => $post_type,  // Optional: Specify REST endpoint slug if needed
        );

        // Register the custom post type again with 'show_in_rest' enabled
        register_post_type( $post_type, $args );

		// Register post meta fields
		register_rest_field( $post_type, 'wbg_author', array(
			'get_callback' => 'get_post_meta_author',
			'update_callback' => 'update_post_meta_author',
			'schema' => null,
			)
		);

		register_rest_field( $post_type, 'wbg_status', array(
			'get_callback' => 'get_post_meta_status',			
			'update_callback' => 'update_post_meta_status',
			'schema' => null,
			)
		);

		register_rest_field( $post_type, 'wbg_download_link', array(
			'update_callback' => 'update_post_meta_dl_link',
			'schema' => null,
			)
		);

		register_rest_field( $post_type, 'wbg_book_categories', array(
			'get_callback' => 'get_wbg_post_book_categories',
			'update_callback' => 'update_wbg_post_book_categories',
			
			//Define schema for field type to be an array of integers or strings
			'schema' => [	
				'type'  => 'array',
				'items' => [
					'type' => ['string', 'integer'], 
				]],
			)
		);
    }
}
add_action( 'rest_api_init', 'enable_cpt_in_rest_api' );

function get_post_meta_author( $object ) {
	return get_wbg_post_meta('wbg_author', $object);
}

function get_post_meta_status( $object ) {
	return get_wbg_post_meta('wbg_status', $object);
}

function update_post_meta_author($meta_value, $object) {
	//error_log("Updating Post Author");
	return update_wbg_post_meta('wbg_author', $meta_value, $object);
}

function update_post_meta_status($meta_value, $object) {
	return update_wbg_post_meta('wbg_status', $meta_value, $object);
}

function update_post_meta_dl_link($meta_value, $object) {

	return update_wbg_post_meta('wbg_download_link', $meta_value, $object);
}

function get_wbg_post_meta($meta_name, $object){
    $post_id = $object['id'];				//Get the ID of the post

    $meta = get_post_meta( $post_id );
	error_log("Getting Post Author");
	error_log("Post ID ".$post_id);

    if ( isset( $meta[$meta_name] ) && isset( $meta[$meta_name][0] ) ) {
        //return the post meta
        return $meta[$meta_name][0];
    }

    // meta not found
    return false;
}

function update_wbg_post_meta($meta_name, $meta_value, $object){
	$post_id = $object->ID;				// Get the ID of the post
	
	error_log("Post ID: ".$post_id);
	error_log("Meta: ".$meta_value);
    
	$havemetafield  = get_post_meta($post_id, $meta_name, false);
    if ($havemetafield) {
        $ret = update_post_meta($post_id, $meta_name, $meta_value );
    } else {
        $ret = add_post_meta($post_id, $meta_name, $meta_value ,true );
    }
    return true;
}

function get_wbg_post_book_categories($object) {
	// Get the post ID 
	// Apparently in get method the $object passed in is a dictionary, 
	// so use must use the key lookup instead of ->
	$post_id = $object['id'];

    // Use built-in WordPress get_the_terms() to get custom taxonomy for the post
	// Aside: To find all custom taxonomies use get_object_taxonomies(get_post_type($post_id))
	$terms = get_the_terms($post_id, 'book_category');

    if (is_wp_error($terms) || empty($terms)) {
        return [];
    }

	return array_map(function($term) {
        return $term->name; // or slug, id, etc.
    }, $terms);
}

function update_wbg_post_book_categories($meta_value, $object) {
	// Get the post ID 
	// Apparently in update method the $object passed in is a JSON object, 
	// so use the -> accesor to get ID)
    $post_id = $object->ID;

	error_log("Post ID: ".$post_id);
	error_log("Categories: ".print_r($meta_value, true));

    // If terms are provided, update them, otherwise, do nothing
    if (!empty($meta_value)) {
        // Set the new terms for the 'book_category' taxonomy
        $ret = wp_set_object_terms($post_id, $meta_value, 'book_category');        
		error_log("Return: ".$ret);
    }

	return true;
}
